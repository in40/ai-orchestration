"""
Backend API service for MCP Agent Web UI
This service acts as a simple proxy to the IT Lead MCP server

Dynamic Planning Architecture:
- Fetches all agents from MCP registry
- Uses LLM to generate task execution plans
- Routes tasks based on agent capabilities
"""

import asyncio
import json
import logging
from enum import Enum
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
import httpx
from datetime import datetime

# Import configuration
import sys
sys.path.insert(0, '/root/qwen/base')
from config import get_settings

# Get settings
settings = get_settings()

# Import dynamic planner
try:
    from .dynamic_planner import DynamicPlanner
except ImportError:
    from dynamic_planner import DynamicPlanner

# Import result storage modules - try relative first, then absolute
try:
    from .git_result_storage import get_git_storage
    from .file_result_storage import get_file_storage
    from .result_router import get_result_router
except ImportError:
    try:
        from git_result_storage import get_git_storage
        from file_result_storage import get_file_storage
        from result_router import get_result_router
    except ImportError:
        # If modules are in different location, add to path
        import sys
        sys.path.insert(0, '/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils')
        from git_result_storage import get_git_storage
        from file_result_storage import get_file_storage
        from result_router import get_result_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global planner instance
_planner: Optional[DynamicPlanner] = None

# IT Lead server configuration (from settings)
IT_LEAD_HOST = settings.IT_LEAD_HOST
IT_LEAD_PORT = settings.IT_LEAD_PORT

# Store active WebSocket connections for real-time updates
active_connections: List[WebSocket] = []

def get_planner() -> DynamicPlanner:
    """Get or create global planner instance"""
    global _planner

    if _planner is None:
        _planner = DynamicPlanner(
            registry_host=settings.REGISTRY_HOST,
            registry_port=settings.REGISTRY_PORT,
            llm_provider_url=settings.LLM_PROVIDER_URL,
            llm_model=settings.LLM_MODEL
        )

    return _planner

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the planner on startup"""
    global _planner
    # Planner is lazily initialized on first use
    logger.info("Dynamic Planning System initialized on first use")
    yield
    # Cleanup on shutdown


app = FastAPI(title="MCP Agent Web UI Backend", version="1.0.0", lifespan=lifespan)

class AgentInfo(BaseModel):
    name: str
    status: str
    last_seen: str
    capabilities: List[str]
    uptime: Optional[str] = None
    version: Optional[str] = None

class TaskAssignment(BaseModel):
    task_id: str
    title: str
    description: str
    assignee: str
    priority: str
    due_date: Optional[str] = None
    context: Optional[dict] = None

class TaskStatusUpdate(BaseModel):
    task_id: str
    status: str
    progress: int
    notes: Optional[str] = None

class ApprovalType(str, Enum):
    code = "code"
    architecture = "architecture"
    deployment = "deployment"
    requirement = "requirement"
    security = "security"

class ApprovalRequest(BaseModel):
    approval_type: ApprovalType
    request_title: str
    request_context: str
    options: List[dict]
    urgency: str = "medium"
    required_approver_roles: List[str] = []

class RequirementType(str, Enum):
    functional = "functional"
    non_functional = "non_functional"
    security = "security"
    performance = "performance"

class RequirementInput(BaseModel):
    requirement_type: RequirementType
    requirement_text: str
    priority: str = "medium"
    acceptance_criteria: List[str] = []
    attachments: List[str] = []
    stakeholder_context: str = ""

class FeedbackTarget(str, Enum):
    code = "code"
    documentation = "documentation"
    architecture = "architecture"
    test = "test"
    process = "process"

class FeedbackType(str, Enum):
    positive = "positive"
    constructive = "constructive"
    critical = "critical"
    suggestion = "suggestion"

class Feedback(BaseModel):
    feedback_target: FeedbackTarget
    feedback_type: FeedbackType
    feedback_content: str
    target_reference: str = ""
    suggested_improvement: str = ""
    priority: str = "medium"

class DashboardView(str, Enum):
    executive = "executive"
    manager = "manager"
    technical = "technical"
    quality = "quality"

class ProjectDashboardRequest(BaseModel):
    dashboard_view: DashboardView = DashboardView.manager
    time_range: str = "week"
    project_filters: List[str] = []
    custom_metrics: List[str] = []

async def refresh_agent_status_from_it_lead():
    """Fetch agent status from the registry server directly"""
    global agent_status
    try:
        # Call the registry server directly to get the list of services
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Call the registry server directly (assuming it's on port 3031)
            registry_response = await client.post(
                f"http://127.0.0.1:3031/mcp",  # Registry server address
                json={
                    "jsonrpc": "2.0",
                    "id": "list_services",
                    "method": "registry/list",
                    "params": {}
                }
            )

            if registry_response.status_code == 200:
                response_data = registry_response.json()
                logger.info(f"Raw response from registry: {response_data}")

                if "result" in response_data and "services" in response_data["result"]:
                    services = response_data["result"]["services"]
                    
                    # Define the mapping from service names to agent roles
                    agent_mapping = {
                        "requirement": "Requirements Engineer",
                        "requirements": "Requirements Engineer",
                        "implementation engineer": "Implementation Engineer"
                    }
                    
                    # Initialize default agent status
                    agent_status = {
                        "IT Lead": {
                            "name": "IT Lead",
                            "status": "online",  # IT Lead is this server, so it's always online
                            "last_seen": datetime.utcnow().isoformat(),
                            "capabilities": ["assign_task", "review_code", "generate_project_plan"],
                            "uptime": "N/A",
                            "version": "N/A",
                            "url": f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp"
                        },
                        "Requirements Engineer": {
                            "name": "Requirements Engineer",
                            "status": "offline",
                            "last_seen": datetime.utcnow().isoformat(),
                            "capabilities": ["analyze_requirements", "validate_requirements"],
                            "uptime": "N/A",
                            "version": "N/A",
                            "url": "N/A"
                        },
                        "Implementation Engineer": {
                            "name": "Implementation Engineer",
                            "status": "offline",
                            "last_seen": datetime.utcnow().isoformat(),
                            "capabilities": ["implement_feature", "generate_code"],
                            "uptime": "N/A",
                            "version": "N/A",
                            "url": "N/A"
                        }
                    }
                    
                    # Process each service and update agent status
                    for service in services:
                        service_name = service.get("name", "").lower()
                        
                        # Find the matching agent role
                        matched_role = None
                        for keyword, role in agent_mapping.items():
                            if keyword in service_name:
                                matched_role = role
                                break
                        
                        # If we found a matching role, update its status to online
                        if matched_role and matched_role in agent_status:
                            agent_status[matched_role] = {
                                "name": matched_role,
                                "status": "online",
                                "last_seen": datetime.utcnow().isoformat(),
                                "capabilities": service.get("capabilities", {}).get("tools", []),
                                "uptime": "N/A",
                                "version": "N/A",
                                "url": service.get("endpoint", "N/A")
                            }
                    
                    logger.info(f"Updated agent status from registry: {agent_status}")
                else:
                    logger.warning("Registry response doesn't contain expected structure")
                    # Fall back to default status if registry response is malformed
                    agent_status = {
                        "IT Lead": {
                            "name": "IT Lead",
                            "status": "online",
                            "last_seen": datetime.utcnow().isoformat(),
                            "capabilities": ["assign_task", "review_code", "generate_project_plan"],
                            "uptime": "N/A",
                            "version": "N/A",
                            "url": f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp"
                        },
                        "Requirements Engineer": {
                            "name": "Requirements Engineer",
                            "status": "offline",
                            "last_seen": datetime.utcnow().isoformat(),
                            "capabilities": ["analyze_requirements", "validate_requirements"],
                            "uptime": "N/A",
                            "version": "N/A",
                            "url": "N/A"
                        },
                        "Implementation Engineer": {
                            "name": "Implementation Engineer",
                            "status": "offline",
                            "last_seen": datetime.utcnow().isoformat(),
                            "capabilities": ["implement_feature", "generate_code"],
                            "uptime": "N/A",
                            "version": "N/A",
                            "url": "N/A"
                        }
                    }
            else:
                logger.error(f"Failed to fetch services from registry: {registry_response.status_code}")
                logger.error(f"Response: {registry_response.text}")
                # Fall back to default status if registry call fails
                agent_status = {
                    "IT Lead": {
                        "name": "IT Lead",
                        "status": "online",
                        "last_seen": datetime.utcnow().isoformat(),
                        "capabilities": ["assign_task", "review_code", "generate_project_plan"],
                        "uptime": "N/A",
                        "version": "N/A",
                        "url": f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp"
                    },
                    "Requirements Engineer": {
                        "name": "Requirements Engineer",
                        "status": "offline",
                        "last_seen": datetime.utcnow().isoformat(),
                        "capabilities": ["analyze_requirements", "validate_requirements"],
                        "uptime": "N/A",
                        "version": "N/A",
                        "url": "N/A"
                    },
                    "Implementation Engineer": {
                        "name": "Implementation Engineer",
                        "status": "offline",
                        "last_seen": datetime.utcnow().isoformat(),
                        "capabilities": ["implement_feature", "generate_code"],
                        "uptime": "N/A",
                        "version": "N/A",
                        "url": "N/A"
                    }
                }

    except httpx.RequestError as e:
        logger.error(f"Error connecting to registry server: {str(e)}")
        # Fall back to default status if there's a connection error
        agent_status = {
            "IT Lead": {
                "name": "IT Lead",
                "status": "online",
                "last_seen": datetime.utcnow().isoformat(),
                "capabilities": ["assign_task", "review_code", "generate_project_plan"],
                "uptime": "N/A",
                "version": "N/A",
                "url": f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp"
            },
            "Requirements Engineer": {
                "name": "Requirements Engineer",
                "status": "offline",
                "last_seen": datetime.utcnow().isoformat(),
                "capabilities": ["analyze_requirements", "validate_requirements"],
                "uptime": "N/A",
                "version": "N/A",
                "url": "N/A"
            },
            "Implementation Engineer": {
                "name": "Implementation Engineer",
                "status": "offline",
                "last_seen": datetime.utcnow().isoformat(),
                "capabilities": ["implement_feature", "generate_code"],
                "uptime": "N/A",
                "version": "N/A",
                "url": "N/A"
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error fetching agents from registry: {str(e)}")
        # Fall back to default status if there's an unexpected error
        agent_status = {
            "IT Lead": {
                "name": "IT Lead",
                "status": "online",
                "last_seen": datetime.utcnow().isoformat(),
                "capabilities": ["assign_task", "review_code", "generate_project_plan"],
                "uptime": "N/A",
                "version": "N/A",
                "url": f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp"
            },
            "Requirements Engineer": {
                "name": "Requirements Engineer",
                "status": "offline",
                "last_seen": datetime.utcnow().isoformat(),
                "capabilities": ["analyze_requirements", "validate_requirements"],
                "uptime": "N/A",
                "version": "N/A",
                "url": "N/A"
            },
            "Implementation Engineer": {
                "name": "Implementation Engineer",
                "status": "offline",
                "last_seen": datetime.utcnow().isoformat(),
                "capabilities": ["implement_feature", "generate_code"],
                "uptime": "N/A",
                "version": "N/A",
                "url": "N/A"
            }
        }

async def broadcast_message(message: dict):
    """Broadcast message to all active WebSocket connections"""
    for connection in active_connections[:]:  # Copy list to prevent modification during iteration
        try:
            await connection.send_text(json.dumps(message))
        except WebSocketDisconnect:
            active_connections.remove(connection)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections for real-time updates"""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Listen for messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Process different types of messages
            if message.get("type") == "get_agents":
                # Refresh agent status from IT Lead server
                await refresh_agent_status_from_it_lead()
                await websocket.send_text(json.dumps({"type": "agent_list", "data": list(agent_status.values())}))
            elif message.get("type") == "get_agent_detail":
                agent_name = message.get("agent_name")
                if agent_name in agent_status:
                    await websocket.send_text(json.dumps({
                        "type": "agent_detail", 
                        "data": agent_status[agent_name]
                    }))
            elif message.get("type") == "refresh_agent_status":
                await refresh_agent_status_from_it_lead()
                agent_name = message.get("agent_name")
                if agent_name and agent_name in agent_status:
                    await websocket.send_text(json.dumps({
                        "type": "agent_detail", 
                        "data": agent_status[agent_name]
                    }))
                else:
                    await websocket.send_text(json.dumps({"type": "agent_list", "data": list(agent_status.values())}))
            elif message.get("type") == "assign_task":
                task_data = message.get("task_data")
                # Process task assignment via IT Lead
                await handle_task_assignment_via_it_lead(task_data)
                # Broadcast update to all clients
                await broadcast_message({
                    "type": "task_assigned",
                    "data": task_data
                })
            elif message.get("type") == "request_human_approval":
                approval_data = message.get("approval_data")
                # Process approval request via IT Lead
                await handle_approval_request_via_it_lead(approval_data)
                # Broadcast update to all clients
                await broadcast_message({
                    "type": "approval_requested",
                    "data": approval_data
                })
            elif message.get("type") == "submit_requirement_input":
                requirement_data = message.get("requirement_data")
                # Process requirement submission via IT Lead
                await handle_requirement_submission_via_it_lead(requirement_data)
                # Broadcast update to all clients
                await broadcast_message({
                    "type": "requirement_submitted",
                    "data": requirement_data
                })
            elif message.get("type") == "provide_feedback":
                feedback_data = message.get("feedback_data")
                # Process feedback via IT Lead
                await handle_feedback_via_it_lead(feedback_data)
                # Broadcast update to all clients
                await broadcast_message({
                    "type": "feedback_provided",
                    "data": feedback_data
                })
            else:
                # Echo back unknown message types
                await websocket.send_text(json.dumps({"type": "error", "message": "Unknown message type"}))
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected")

async def handle_task_assignment_via_it_lead(task_data: dict):
    """Handle enhanced task assignment by calling IT Lead server with full context"""
    logger.info(f"Assigning task via IT Lead: {task_data}")
    logger.info(f"Task context: {task_data.get('context', {})}")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:  # Increased timeout for complex tasks
            # Build comprehensive arguments including all metadata and context
            base_arguments = {
                "task_id": task_data.get("id", task_data.get("task_id")),
                "task_description": task_data.get("description"),
                "assignee": task_data.get("assignee"),  # IT Lead will intelligently route based on content analysis
                "priority": task_data.get("priority", "medium")
            }

            # Add optional fields if present
            if task_data.get("dueDate"):
                base_arguments["deadline"] = task_data.get("dueDate")

            # Include full context metadata for intelligent routing
            context = task_data.get("context", {})
            logger.info(f"Context received: {context}")
            if context:
                base_arguments["metadata"] = {
                    "tags": context.get("tags", []),
                    "code_diff": context.get("code_diff"),
                    "programming_language": context.get("programming_language"),
                    "framework": context.get("framework"),
                    "acceptance_criteria": context.get("acceptance_criteria"),
                    "business_context": context.get("business_context"),
                    "deploy_after_implementation": context.get("deploy_after_implementation", False)
                }
                logger.info(f"Built metadata with deploy_after_implementation={base_arguments['metadata'].get('deploy_after_implementation')}")

            # Add dependencies if present
            if task_data.get("dependencies"):
                base_arguments["metadata"]["dependencies"] = task_data.get("dependencies")

            logger.info(f"Sending to IT Lead: base_arguments={base_arguments}")

            response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": task_data.get("id", task_data.get("task_id")),
                    "method": "tools/call",
                    "params": {
                        "name": "assign_task",  # Submit to IT Lead for intelligent routing
                        "arguments": base_arguments
                    }
                }
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Task successfully submitted to IT Lead: {task_data.get('id')}")
                
                # Log assignment details from the response
                if "result" in result and isinstance(result["result"], dict):
                    assign_result = result["result"]
                    logger.info(f"Assignment status: {assign_result.get('status', 'unknown')}")
                    logger.info(f"Assigned to: {assign_result.get('assigned_to', 'unassigned')}")
                    
                    # Log routing decision details
                    if "metadata" in assign_result:
                        metadata = assign_result["metadata"]
                        if isinstance(metadata, dict):
                            llm_plan = metadata.get("llm_plan")
                            if llm_plan and isinstance(llm_plan, dict):
                                logger.info(f"LLM Plan: primary_agent={llm_plan.get('primary_agent')}, tools={list(llm_plan.get('tools', {}).keys())}")
                            
                            routing_decision = metadata.get("routing_decision")
                            if routing_decision and isinstance(routing_decision, dict):
                                confidence = routing_decision.get("confidence", 0)
                                logger.info(f"Routing confidence: {confidence:.2f}")

                return {"success": True, "result": result}
            else:
                error_msg = f"Failed to submit task to IT Lead: {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text[:500]}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}

    except httpx.RequestError as e:
        error_msg = f"Error sending task to IT Lead: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

async def handle_approval_request_via_it_lead(approval_data: dict):
    """Handle approval request by calling IT Lead server"""
    logger.info(f"Handling approval request via IT Lead: {approval_data}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Call the request_human_approval tool on the IT Lead server
            response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "approval_request",
                    "method": "tools/call",
                    "params": {
                        "name": "request_human_approval",
                        "arguments": approval_data
                    }
                }
            )
            
            if response.status_code == 200:
                logger.info("Approval request sent successfully via IT Lead")
            else:
                logger.error(f"Failed to send approval request via IT Lead: {response.status_code}")
                
    except httpx.RequestError as e:
        logger.error(f"Error sending approval request to IT Lead: {str(e)}")

async def handle_requirement_submission_via_it_lead(requirement_data: dict):
    """Handle requirement submission by calling IT Lead server"""
    logger.info(f"Handling requirement submission via IT Lead: {requirement_data}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Call the submit_requirement_input tool on the IT Lead server
            response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "requirement_submit",
                    "method": "tools/call",
                    "params": {
                        "name": "submit_requirement_input",
                        "arguments": requirement_data
                    }
                }
            )
            
            if response.status_code == 200:
                logger.info("Requirement submitted successfully via IT Lead")
            else:
                logger.error(f"Failed to submit requirement via IT Lead: {response.status_code}")
                
    except httpx.RequestError as e:
        logger.error(f"Error submitting requirement to IT Lead: {str(e)}")

async def handle_feedback_via_it_lead(feedback_data: dict):
    """Handle feedback by calling IT Lead server"""
    logger.info(f"Handling feedback via IT Lead: {feedback_data}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Call the provide_feedback tool on the IT Lead server
            response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "feedback_submit",
                    "method": "tools/call",
                    "params": {
                        "name": "provide_feedback",
                        "arguments": feedback_data
                    }
                }
            )
            
            if response.status_code == 200:
                logger.info("Feedback submitted successfully via IT Lead")
            else:
                logger.error(f"Failed to submit feedback via IT Lead: {response.status_code}")
                
    except httpx.RequestError as e:
        logger.error(f"Error submitting feedback to IT Lead: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint for health check"""
    return {"message": "MCP Agent Web UI Backend is running", "status": "healthy"}

@app.get("/api/agents")
async def get_agents():
    """Get list of all agents and their status from IT Lead server"""
    # Refresh status from IT Lead server before returning
    await refresh_agent_status_from_it_lead()
    return list(agent_status.values())

@app.get("/api/agents/{agent_name}")
async def get_agent_detail(agent_name: str):
    """Get detailed information about a specific agent from IT Lead server"""
    # Refresh status from IT Lead server
    await refresh_agent_status_from_it_lead()
    
    if agent_name not in agent_status:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent_status[agent_name]

@app.post("/api/agents/{agent_name}/refresh")
async def refresh_agent(agent_name: str):
    """Manually refresh the status of a specific agent from IT Lead server"""
    # Refresh status from IT Lead server
    await refresh_agent_status_from_it_lead()
    
    if agent_name not in agent_status:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"message": f"Refreshed status for {agent_name}", "data": agent_status[agent_name]}

@app.post("/api/tasks/assign")
async def assign_task_endpoint(task: TaskAssignment):
    """Endpoint to assign a task via IT Lead server"""
    logger.info(f"Task assigned via IT Lead: {task.title} to {task.assignee}")
    
    # Validate that the assignee is a known agent role (case-insensitive for IT Lead)
    await refresh_agent_status_from_it_lead()
    
    # Normalize assignee for comparison (IT Lead variations)
    normalized_assignee = task.assignee.lower()
    valid_assignees = {k.lower(): k for k in agent_status.keys()}
    
    if normalized_assignee not in valid_assignees:
        raise HTTPException(status_code=400, detail=f"Unknown agent: {task.assignee}")
    
    # Use canonical name for agent_status lookup
    canonical_assignee = valid_assignees[normalized_assignee]
    if task.assignee != canonical_assignee:
        logger.info(f"Normalized assignee '{task.assignee}' to '{canonical_assignee}'")
        task.assignee = canonical_assignee
    
    # Simulate task assignment
    task_dict = task.dict()
    task_dict["status"] = "assigned"
    
    # Send the task assignment to IT Lead server
    await handle_task_assignment_via_it_lead(task_dict)
    
    # Broadcast the task assignment to all connected clients
    await broadcast_message({
        "type": "task_assigned",
        "data": task_dict
    })
    
    return {"message": "Task assigned successfully", "task_id": task.task_id}

@app.post("/api/approvals/request")
async def request_approval_endpoint(approval: ApprovalRequest):
    """Endpoint to request human approval via IT Lead server"""
    logger.info(f"Requesting approval via IT Lead: {approval.request_title}")
    
    # Send the approval request to IT Lead server
    await handle_approval_request_via_it_lead(approval.dict())
    
    # Broadcast the approval request to all connected clients
    await broadcast_message({
        "type": "approval_requested",
        "data": approval.dict()
    })
    
    return {"message": "Approval request submitted successfully", "request_id": f"approval-{hash(str(approval.dict())) % 10000}"}

@app.post("/api/requirements/submit")
async def submit_requirement_endpoint(requirement: RequirementInput):
    """Endpoint to submit requirements via IT Lead server"""
    logger.info(f"Submitting requirement via IT Lead: {requirement.requirement_text[:50]}...")
    
    # Send the requirement to IT Lead server
    await handle_requirement_submission_via_it_lead(requirement.dict())
    
    # Broadcast the requirement submission to all connected clients
    await broadcast_message({
        "type": "requirement_submitted",
        "data": requirement.dict()
    })
    
    return {"message": "Requirement submitted successfully", "requirement_id": f"req-{hash(str(requirement.dict())) % 10000}"}

@app.post("/api/feedback/provide")
async def provide_feedback_endpoint(feedback: Feedback):
    """Endpoint to provide feedback via IT Lead server"""
    logger.info(f"Providing feedback via IT Lead on {feedback.feedback_target}")
    
    # Send the feedback to IT Lead server
    await handle_feedback_via_it_lead(feedback.dict())
    
    # Broadcast the feedback to all connected clients
    await broadcast_message({
        "type": "feedback_provided",
        "data": feedback.dict()
    })
    
    return {"message": "Feedback provided successfully", "feedback_id": f"feedback-{hash(str(feedback.dict())) % 10000}"}

@app.post("/api/tasks/update")
async def update_task_status_endpoint(update: TaskStatusUpdate):
    """Update the status of a task"""
    logger.info(f"Task status updated: {update.task_id} - {update.status}")
    
    # Broadcast the task update to all connected clients
    await broadcast_message({
        "type": "task_updated",
        "data": update.dict()
    })

@app.post("/api/tasks/delete")
async def delete_task_endpoint(task_data: dict):
    """Delete a task from IT Lead server"""
    task_id = task_data.get("task_id")
    if not task_id:
        raise HTTPException(status_code=400, detail="task_id is required")
    
    logger.info(f"Deleting task: {task_id}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": f"delete-task-{task_id}",
                    "method": "tools/call",
                    "params": {
                        "name": "delete_task",
                        "arguments": {"task_id": task_id}
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Task deleted: {result}")
                return {"message": f"Task {task_id} has been deleted", "success": True}
            else:
                logger.error(f"Failed to delete task: {response.status_code}")
                raise HTTPException(status_code=500, detail=f"Failed to delete task")
    except Exception as e:
        logger.error(f"Error deleting task: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    
    return {"message": "Task status updated successfully", "task_id": update.task_id}

async def fetch_tasks_from_it_lead():
    """Fetch actual tasks from IT Lead server's task storage"""
    logger.info("Fetching tasks from IT Lead server")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Call the IT Lead server to get all tasks using the new get_all_tasks tool
            response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "fetch-all-tasks",
                    "method": "tools/call",
                    "params": {
                        "name": "get_all_tasks",  # Using the new get_all_tasks tool
                        "arguments": {}
                    }
                }
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Fetched tasks response: {result}")

                # Extract tasks from the response
                if "result" in result and "result" in result["result"]:
                    tasks_result = result["result"]["result"]

                    # Format tasks to match the expected structure
                    formatted_tasks = []
                    if "tasks" in tasks_result:
                        for task in tasks_result["tasks"]:
                            metadata = task.get("metadata", {})
                            formatted_tasks.append({
                                "id": task.get("task_id", "unknown"),
                                "title": task.get("title", f"Task: {task.get('task_id', 'unknown')}"),
                                "assignee": task.get("assigned_to", "Unknown"),
                                "status": task.get("status", "pending"),
                                "priority": task.get("priority", "medium"),
                                "progress": task.get("progress_percentage", 0),
                                "git_url": metadata.get("git_url"),
                                "deployment_url": metadata.get("deployment_url"),
                                "storage_type": metadata.get("storage_type")
                            })
                    return formatted_tasks
                else:
                    logger.warning("Response doesn't contain expected structure")
                    return []
            else:
                logger.error(f"Failed to fetch tasks from IT Lead: {response.status_code}")
                return []

    except httpx.RequestError as e:
        logger.error(f"Error connecting to IT Lead server: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching tasks: {str(e)}")
        return []

async def fetch_deployments_from_it_lead(status_filter: str = "running"):
    """Fetch deployments from IT Lead server (which proxies to DevOps Engineer)"""
    logger.info(f"Fetching deployments from IT Lead server (status_filter={status_filter})")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Call IT Lead's list_deployments tool (which proxies to DevOps)
            response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "fetch-deployments",
                    "method": "tools/call",
                    "params": {
                        "name": "list_deployments",
                        "arguments": {"status_filter": status_filter}
                    }
                }
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Fetched deployments response: {result}")

                # Extract deployments from the response
                if "result" in result:
                    deployments_result = result["result"]
                    deployments = deployments_result.get("deployments", [])
                    logger.info(f"Found {len(deployments)} deployments")
                    return deployments
                else:
                    logger.warning("Response doesn't contain expected structure")
                    return []
            else:
                logger.error(f"Failed to fetch deployments from IT Lead: {response.status_code}")
                return []

    except httpx.RequestError as e:
        logger.error(f"Error connecting to IT Lead server: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching deployments: {str(e)}")
        return []


@app.get("/api/tasks")
async def get_tasks():
    """Get list of actual tasks from the system via IT Lead server"""
    tasks = await fetch_tasks_from_it_lead()

    # If no tasks were retrieved from IT Lead, return an empty list
    # rather than hardcoded mock data
    if not tasks:
        logger.info("No tasks retrieved from IT Lead server, returning empty list")
        return []

    return tasks


@app.get("/api/deployments")
async def get_deployments(status_filter: str = "running"):
    """Get list of deployed applications via IT Lead server (proxies to DevOps Engineer)"""
    deployments = await fetch_deployments_from_it_lead(status_filter=status_filter)

    # Return deployments list
    if not deployments:
        logger.info("No deployments retrieved, returning empty list")
        return []

    return deployments


@app.get("/api/tasks/{task_id}/progress")
async def get_task_progress(task_id: str):
    """Get detailed task progress with MCP-based communication tracking
    
    This endpoint fetches the complete task lifecycle including:
    - Assignment history
    - Agent communications via MCP tools
    - Status changes at each step
    - Tool call results from downstream agents
    """
    logger.info(f"Fetching detailed progress for task: {task_id}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # First, get the main task info using get_all_tasks
            tasks_response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": f"task-info-{task_id}",
                    "method": "tools/call",
                    "params": {
                        "name": "get_all_tasks",
                        "arguments": {"status_filter": None}
                    }
                }
            )

            if tasks_response.status_code != 200:
                logger.error(f"Failed to fetch task info: {tasks_response.status_code}")
                raise HTTPException(status_code=500, detail="Failed to fetch task information")

            # Get task history
            history_response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": f"task-history-{task_id}",
                    "method": "tools/call",
                    "params": {
                        "name": "get_task_history",
                        "arguments": {"task_id": task_id}
                    }
                }
            )

            if history_response.status_code != 200:
                logger.error(f"Failed to fetch task history: {history_response.status_code}")
                raise HTTPException(status_code=500, detail="Failed to fetch task history")

        # Parse responses
        tasks_data = tasks_response.json()
        history_data = history_response.json()

        # Extract task details from get_all_tasks response
        task_info = None
        if "result" in tasks_data and "result" in tasks_data["result"]:
            for t in tasks_data["result"]["result"].get("tasks", []):
                if t.get("task_id") == task_id:
                    task_info = t
                    break

        # Extract history from get_task_history response
        status_history = []
        if "result" in history_data and "result" in history_data["result"]:
            hist_result = history_data["result"]["result"]
            status_history = hist_result.get("status_history", [])

        # Build progress report with MCP communication tracking
        progress_report = {
            "task_id": task_info.get("task_id", task_id) if task_info else task_id,
            "title": task_info.get("title", f"Task: {task_id}") if task_info else "",
            "description": task_info.get("description", "") if task_info else "",
            "status": task_info.get("status", "unknown") if task_info else "unknown",
            "assigned_to": task_info.get("assigned_to", "unassigned") if task_info else "unassigned",
            "priority": task_info.get("priority", "medium") if task_info else "medium",
            "created_at": task_info.get("created_at") if task_info else None,
            "updated_at": task_info.get("updated_at") if task_info else None,
            
            # Status history shows when and how status changed
            "status_history": [
                {
                    "timestamp": entry.get("timestamp"),
                    "status": entry.get("status"),
                    "reason": entry.get("reason")
                }
                for entry in status_history
            ],
            
            # Metadata contains routing decisions and tool calls
            "metadata": task_info.get("metadata", {}) if task_info else {},
            
            # Progress calculation based on lifecycle stages
            "progress_percent": calculate_task_progress(task_info, status_history) if task_info else 0,
            
            # MCP communication details (from metadata)
            "mcp_communications": extract_mcp_communications(
                task_info.get("metadata", {}) if task_info else {}
            )
        }

        logger.info(f"Progress report generated for {task_id}: status={progress_report['status']}, progress={progress_report['progress_percent']}%")
        return progress_report

    except httpx.RequestError as e:
        logger.error(f"Error connecting to IT Lead server: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error connecting to IT Lead server: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching task progress: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


def calculate_task_progress(task_info: Dict[str, Any], status_history: List[Dict]) -> int:
    """Calculate task completion progress based on lifecycle stages"""
    if not task_info or not status_history:
        return 0

    current_status = task_info.get("status", "")
    
    # Define progression weights
    stage_weights = {
        "pending_routing": 5,
        "received": 10,
        "assigned": 20,
        "forwarded": 40,
        "in_progress": 60,
        "completed": 100,
        "failed": 80,  # Partial progress even on failure
    }
    
    return stage_weights.get(current_status, 5)


def extract_mcp_communications(metadata: Dict[str, Any]) -> List[Dict]:
    """Extract MCP communication details from task metadata"""
    communications = []
    
    if not metadata:
        return communications
    
    # Extract routing decision (initial assignment)
    routing_decision = metadata.get("routing_decision", {})
    if routing_decision:
        communications.append({
            "type": "route_assignment",
            "timestamp": None,  # Will be filled from status_history
            "rule_id": routing_decision.get("matched_rule_id"),
            "confidence": routing_decision.get("confidence"),
            "requires_llm_planning": routing_decision.get("requires_llm_planning", False),
            "assigned_to": metadata.get("llm_plan", {}).get("primary_agent") if metadata.get("llm_plan") else None
        })
    
    # Extract LLM planning details if present
    llm_plan = metadata.get("llm_plan")
    if llm_plan:
        communications.append({
            "type": "llm_planning",
            "timestamp": llm_plan.get("timestamp"),
            "primary_agent": llm_plan.get("primary_agent"),
            "sequence": llm_plan.get("sequence", []),
            "tools": llm_plan.get("tools", {}),
            "reasoning": llm_plan.get("reasoning")
        })
    
    # Extract tool call details
    tool_call = metadata.get("tool_call")
    if tool_call:
        communications.append({
            "type": "tool_execution",
            "method": tool_call,
            "arguments": metadata.get("original_arguments", {})
        })
    
    return communications


@app.get("/api/tasks/{task_id}/history")
async def get_task_history(task_id: str):
    """Get task history from IT Lead server"""
    logger.info(f"Fetching history for task: {task_id}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": f"history-{task_id}",
                    "method": "tools/call",
                    "params": {
                        "name": "get_task_history",
                        "arguments": {
                            "task_id": task_id
                        }
                    }
                }
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Task history response: {result}")
                
                if "result" in result and "result" in result["result"]:
                    history_result = result["result"]["result"]
                    
                    # Format the history for the frontend
                    formatted_history = {
                        "task_id": history_result.get("task_id", task_id),
                        "title": history_result.get("title", ""),
                        "current_status": history_result.get("current_status", "unknown"),
                        "submitter": history_result.get("submitter", "unknown"),
                        "submitter_type": history_result.get("submitter_type", "unknown"),
                        "transport_channel": history_result.get("transport_channel", "unknown"),
                        "assigned_to": history_result.get("assigned_to", "unassigned"),
                        "created_at": history_result.get("created_at"),
                        "updated_at": history_result.get("updated_at"),
                        "status_history": history_result.get("status_history", [])
                    }
                    return formatted_history
                else:
                    logger.warning("Unexpected response format")
                    return {"error": "Unexpected response format"}
            else:
                logger.error(f"Failed to fetch task history: {response.status_code}")
                raise HTTPException(status_code=500, detail="Failed to fetch task history")

    except httpx.RequestError as e:
        logger.error(f"Error connecting to IT Lead server: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error connecting to IT Lead server: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching task history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/api/tasks/progress")
async def get_all_tasks_with_progress():
    """Get all tasks with their progress information via MCP
    
    This endpoint provides a comprehensive view of all tasks including:
    - Basic task info (title, assignee, status)
    - Progress percentage based on lifecycle
    - Status history timeline
    - MCP communication details from metadata
    """
    logger.info("Fetching all tasks with progress information")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get all tasks via IT Lead's get_all_tasks tool (MCP-based)
            response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "all-tasks-progress",
                    "method": "tools/call",
                    "params": {
                        "name": "get_all_tasks",
                        "arguments": {"status_filter": None}
                    }
                }
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch tasks: {response.status_code}")
                raise HTTPException(status_code=500, detail="Failed to fetch tasks")

        result = response.json()

        # Extract tasks and format with progress
        tasks_with_progress = []
        if "result" in result and "result" in result["result"]:
            for task_data in result["result"]["result"].get("tasks", []):
                status_history = task_data.get("status_history", [])
                
                # Calculate progress based on current status
                current_status = task_data.get("status", "")
                stage_weights = {
                    "pending_routing": 5,
                    "received": 10,
                    "assigned": 20,
                    "forwarded": 40,
                    "in_progress": 60,
                    "completed": 100,
                    "failed": 80
                }
                
                progress_percent = stage_weights.get(current_status, 5)
                
                # Extract MCP communications from metadata
                mcp_communications = extract_mcp_communications(
                    task_data.get("metadata", {})
                )

                tasks_with_progress.append({
                    "task_id": task_data.get("task_id"),
                    "title": task_data.get("title"),
                    "description": task_data.get("description"),
                    "status": current_status,
                    "assigned_to": task_data.get("assigned_to"),
                    "priority": task_data.get("priority", "medium"),
                    "progress_percent": progress_percent,
                    "created_at": task_data.get("created_at"),
                    "updated_at": task_data.get("updated_at"),
                    "status_history": [
                        {
                            "timestamp": entry.get("timestamp"),
                            "status": entry.get("status"),
                            "reason": entry.get("reason")
                        }
                        for entry in status_history
                    ],
                    "mcp_communications": mcp_communications,
                    "metadata": task_data.get("metadata", {})
                })

        logger.info(f"Retrieved {len(tasks_with_progress)} tasks with progress info")
        return {"tasks": tasks_with_progress, "total": len(tasks_with_progress)}

    except httpx.RequestError as e:
        logger.error(f"Error connecting to IT Lead server: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error connecting to IT Lead server: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching tasks with progress: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.post("/api/dashboard/view")
async def get_dashboard_data(request: ProjectDashboardRequest):
    """Get project dashboard data - for now, return a simple response"""
    logger.info(f"Getting dashboard data for view: {request.dashboard_view}")

    # In a real implementation, this would call the IT Lead server
    # For now, return mock data
    return {
        "dashboard_view": request.dashboard_view,
        "time_range": request.time_range,
        "project_filters": request.project_filters,
        "custom_metrics": request.custom_metrics,
        "data": {
            "projects": 3,
            "active_tasks": 12,
            "completed_tasks": 8,
            "team_members_online": 4,
            "overall_progress": 68
        }
    }


# ============================================================================
# Dynamic Planning System Endpoints
# ============================================================================

@app.get("/api/planner/agents")
async def get_all_agents_from_registry():
    """
    Get all available agents from MCP registry using dynamic discovery
    
    This endpoint fetches agents directly from the registry without
    any hardcoded mappings, providing a complete view of all available agents.
    """
    try:
        planner = get_planner()
        agents = await planner.get_available_agents()
        
        logger.info(f"Discovered {len(agents)} agents from registry")
        return {
            "success": True,
            "agents": agents,
            "count": len(agents)
        }
    except Exception as e:
        logger.error(f"Error fetching agents from registry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch agents: {str(e)}")


class TaskRoutingRequest(BaseModel):
    """Request for task routing"""
    task_id: str
    title: str
    description: str
    context: Optional[dict] = None


class TaskRoutingResponse(BaseModel):
    """Response for task routing"""
    success: bool
    task_id: str
    plan: Dict[str, Any]
    agents: List[Dict[str, Any]]
    routing_confidence: float
    complexity: str


@app.post("/api/planner/route", response_model=TaskRoutingResponse)
async def route_task_dynamic(request: TaskRoutingRequest):
    """
    Route a task using dynamic planning with LLM
    
    This endpoint uses the dynamic planning system to:
    1. Fetch all available agents from MCP registry
    2. Get comprehensive capabilities for each agent
    3. Use LLM to generate an execution plan
    4. Select optimal agent(s) for task execution
    
    Returns the routing decision with explanation.
    """
    try:
        planner = get_planner()
        
        task = {
            "id": request.task_id,
            "title": request.title,
            "description": request.description,
            "context": request.context or {}
        }
        
        routing_decision = await planner.route_task(task)
        
        if not routing_decision.get("success"):
            return TaskRoutingResponse(
                success=False,
                task_id=request.task_id,
                plan={},
                agents=[],
                routing_confidence=0.0,
                complexity="unknown"
            )
        
        plan = routing_decision.get("plan", {})
        
        return TaskRoutingResponse(
            success=True,
            task_id=request.task_id,
            plan=plan,
            agents=routing_decision.get("agents", []),
            routing_confidence=plan.get("confidence", 0.0),
            complexity=plan.get("complexity", "unknown")
        )
    except Exception as e:
        logger.error(f"Error routing task: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to route task: {str(e)}")


class DynamicPlanPreviewRequest(BaseModel):
    """Request for dynamic plan preview"""
    task_id: str
    title: str
    description: str
    context: Optional[dict] = None


@app.post("/api/planner/preview")
async def preview_dynamic_plan(request: DynamicPlanPreviewRequest):
    """
    Preview the dynamic planning process without executing the task
    
    This endpoint shows what the dynamic planner would do:
    - Which agents would be selected
    - What the execution plan would look like
    - Why these agents were chosen
    
    Useful for understanding and debugging the routing decision.
    """
    try:
        planner = get_planner()
        
        task = {
            "id": request.task_id,
            "title": request.title,
            "description": request.description,
            "context": request.context or {}
        }
        
        # Get available agents
        agents = await planner.get_available_agents()
        
        # Get plan preview (without executing the task)
        plan = await planner.plan_generator.generate_task_plan(task, agents)
        
        return {
            "success": True,
            "task_id": request.task_id,
            "plan": plan,
            "agents": agents,
            "preview": True
        }
    except Exception as e:
        logger.error(f"Error previewing dynamic plan: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to preview plan: {str(e)}")


@app.get("/api/planner/agents/{agent_name}")
async def get_agent_detail_dynamic(agent_name: str):
    """
    Get detailed information about a specific agent from registry
    
    This endpoint fetches the full agent information from the registry,
    including all capabilities, tools, resources, and prompts.
    """
    try:
        planner = get_planner()
        agents = await planner.get_available_agents()
        
        # Find the requested agent
        agent = next((a for a in agents if a["name"] == agent_name), None)
        
        if agent is None:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")
        
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching agent detail: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch agent: {str(e)}")


@app.get("/api/results/list")
async def list_results(
    task_id: Optional[str] = None,
    agent: Optional[str] = None,
    limit: int = 100
):
    """List stored results with optional filtering"""
    try:
        router = get_result_router()
        results = router.list_results(task_id=task_id, agent=agent)
        
        # Limit results
        return {"results": results[:limit]}
    except Exception as e:
        logger.error(f"Error listing results: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to list results: {str(e)}")


@app.get("/api/results/get")
async def get_result(task_id: str, result_type: str = "code"):
    """Get a specific stored result"""
    try:
        router = get_result_router()
        content = router.get_result(task_id, result_type)
        
        if content is None:
            raise HTTPException(status_code=404, detail=f"Result not found: {task_id}")
        
        return {"task_id": task_id, "result": content, "type": result_type}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting result: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get result: {str(e)}")


@app.get("/api/results/git/history")
async def get_git_history(task_id: str):
    """Get Git history for a task result"""
    try:
        storage = get_git_storage()
        repo = storage._get_git_repo()
        
        if not repo:
            raise HTTPException(status_code=404, detail="Git repository not available")
        
        from git import Git
        git = Git(storage.repo_path)
        
        # Get log for task directory
        log = git.log("--oneline", f"results/{task_id}/")
        
        return {
            "task_id": task_id,
            "history": [
                {"sha": line.split()[0], "message": " ".join(line.split()[1:])}
                for line in log.strip().split("\n") if line
            ]
        }
    except ImportError:
        raise HTTPException(status_code=500, detail="GitPython not installed. Install with: pip install GitPython")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting git history: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get git history: {str(e)}")




# ============================================================================
# HTTP Git File Access Endpoints  
# ============================================================================

@app.get("/api/git/files/{task_id:path}")
async def get_git_file(task_id: str):
    """Serve files from Git repository via HTTP"""
    logger.info(f"Serving Git file: {task_id}")
    try:
        parts = task_id.split("/", 1)
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid path. Use: {task_uuid}/{filename}")
        task_uuid, filename = parts
        file_path = f"/tmp/mcp-vibe-coding-git/repo/results/{task_uuid}/{filename}"
        import os
        if not os.path.exists(file_path):
            file_path = f"/root/qwen/base/mcp-results/results/{task_uuid}/{filename}"
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="File not found")
        with open(file_path, 'rb') as f:
            content = f.read()
        ext = '.' + filename.split('.')[-1] if '.' in filename else ''
        ct = {'.md':'text/markdown','.html':'text/html','.css':'text/css','.js':'application/javascript','.json':'application/json','.yaml':'text/yaml','.yml':'text/yaml','.py':'text/x-python','.txt':'text/plain'}.get(ext, 'application/octet-stream')
        from fastapi.responses import Response
        return Response(content=content, media_type=ct, headers={"Content-Disposition": f"inline; filename={filename}"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving Git file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/git/browse/{task_id}")
async def browse_git_directory(task_id: str):
    """Browse task directory"""
    logger.info(f"Browsing Git directory: {task_id}")
    try:
        import os
        dir_path = f"/tmp/mcp-vibe-coding-git/repo/results/{task_id}"
        if not os.path.exists(dir_path):
            dir_path = f"/root/qwen/base/mcp-results/results/{task_id}"
            if not os.path.exists(dir_path):
                raise HTTPException(status_code=404, detail="Task not found")
        files = []
        for item in os.listdir(dir_path):
            item_path = os.path.join(dir_path, item)
            files.append({"name": item, "type": "dir" if os.path.isdir(item_path) else "file", "size": os.path.getsize(item_path) if os.path.isfile(item_path) else 0, "url": f"/api/git/files/{task_id}/{item}"})
        return {"task_id": task_id, "files": files}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error browsing directory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/{task_id}/redeploy")
async def redeploy_task(task_id: str):
    """Redeploy a task that has a git_url but no active deployment"""
    logger.info(f"Redeploying task: {task_id}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First get the task to fetch git_url
            tasks_response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": f"get-task-{task_id}",
                    "method": "tools/call",
                    "params": {
                        "name": "get_all_tasks",
                        "arguments": {"status_filter": None}
                    }
                }
            )
            
            if tasks_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to fetch task information")
            
            tasks_result = tasks_response.json()
            tasks = tasks_result.get("result", {}).get("tasks", [])
            task = next((t for t in tasks if t.get("task_id") == task_id), None)
            
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            
            git_url = task.get("metadata", {}).get("git_url")
            if not git_url:
                raise HTTPException(status_code=400, detail="Task has no git_url")
            
            # Call DevOps to deploy from git
            deploy_response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": f"deploy-{task_id}",
                    "method": "tools/call",
                    "params": {
                        "name": "deploy_web_application",
                        "arguments": {
                            "task_id": task_id,
                            "git_url": git_url,
                            "container_port": 5000
                        }
                    }
                }
            )
            
            if deploy_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to deploy")
            
            deploy_result = deploy_response.json()
            
            return {
                "success": True,
                "message": "Task redeployed successfully",
                "deployment": deploy_result.get("result", {})
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error redeploying task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/deployments/{task_id}/start")
async def start_deployment(task_id: str):
    """Start a stopped deployment"""
    logger.info(f"Starting deployment for task: {task_id}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get deployment info
            deployment = await get_deployment_info(task_id)
            if not deployment:
                raise HTTPException(status_code=404, detail="Deployment not found")
            
            container_id = deployment.get("container_id")
            if not container_id:
                raise HTTPException(status_code=400, detail="No container ID found")
            
            # Start the container via DevOps
            start_response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": f"start-{task_id}",
                    "method": "tools/call",
                    "params": {
                        "name": "start_deployment",
                        "arguments": {"container_id": container_id}
                    }
                }
            )
            
            if start_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to start deployment")
            
            return {
                "success": True,
                "message": "Deployment started successfully"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting deployment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/deployments/{task_id}/stop")
async def stop_deployment(task_id: str):
    """Stop a running deployment"""
    logger.info(f"Stopping deployment for task: {task_id}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            deployment = await get_deployment_info(task_id)
            if not deployment:
                raise HTTPException(status_code=404, detail="Deployment not found")
            
            container_id = deployment.get("container_id")
            if not container_id:
                raise HTTPException(status_code=400, detail="No container ID found")
            
            stop_response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": f"stop-{task_id}",
                    "method": "tools/call",
                    "params": {
                        "name": "stop_deployment",
                        "arguments": {"container_id": container_id}
                    }
                }
            )
            
            if stop_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to stop deployment")
            
            return {
                "success": True,
                "message": "Deployment stopped successfully"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping deployment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/deployments/{task_id}")
async def delete_deployment(task_id: str):
    """Delete/remove a deployment"""
    logger.info(f"Deleting deployment for task: {task_id}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            deployment = await get_deployment_info(task_id)
            if not deployment:
                raise HTTPException(status_code=404, detail="Deployment not found")
            
            container_id = deployment.get("container_id")
            if not container_id:
                raise HTTPException(status_code=400, detail="No container ID found")
            
            delete_response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": f"delete-{task_id}",
                    "method": "tools/call",
                    "params": {
                        "name": "delete_deployment",
                        "arguments": {"container_id": container_id}
                    }
                }
            )
            
            if delete_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to delete deployment")
            
            return {
                "success": True,
                "message": "Deployment deleted successfully"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting deployment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/refresh-status")
async def refresh_task_status():
    """Refresh all task statuses from IT Lead server"""
    logger.info("Refreshing task statuses from IT Lead server")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Trigger IT Lead to refresh task statuses
            refresh_response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "refresh-tasks",
                    "method": "tools/call",
                    "params": {
                        "name": "get_all_tasks",
                        "arguments": {"status_filter": None}
                    }
                }
            )
            
            if refresh_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to refresh tasks")
            
            return {
                "success": True,
                "message": "Task statuses refreshed successfully"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing task statuses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/deployments/refresh")
async def refresh_deployments():
    """Refresh deployment list from DevOps Engineer"""
    logger.info("Refreshing deployments from DevOps Engineer")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            refresh_response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "refresh-deployments",
                    "method": "tools/call",
                    "params": {
                        "name": "list_deployments",
                        "arguments": {"status_filter": "all"}
                    }
                }
            )
            
            if refresh_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to refresh deployments")
            
            return {
                "success": True,
                "message": "Deployments refreshed successfully"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing deployments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_deployment_info(task_id: str) -> dict:
    """Helper to get deployment info for a task"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": f"get-deployment-{task_id}",
                "method": "tools/call",
                "params": {
                    "name": "get_deployment",
                    "arguments": {"task_id": task_id}
                }
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("result", {})
    return {}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)