# Agent Git Push Integration Guide

## Overview

This guide explains how MCP agents can push results directly to Git instead of using the centralized ResultRouter.

## Architecture Comparison

### Current Architecture (Centralized)
```
Agent executes tool → Returns result → IT Lead stores via ResultRouter
    ↓
ResultRouter classifies content → Git Storage OR File Storage
    ↓
IT Lead stores storage reference in DB
```

### New Architecture (Agent-Driven)
```
Agent executes tool → Uses AgentGitHelper → Pushes to Git directly
    ↓
Agent returns Git URL in result → IT Lead stores URL in DB
```

## Benefits of Agent-Driven Git Push

| Benefit | Description |
|---------|-------------|
| **Simpler** | No intermediate storage routing layer |
| **Direct ownership** | Agent commits under their identity |
| **Lower latency** | No intermediate processing |
| **Full control** | Agent controls their commits |

## Agent Architecture

The MCP system uses **separate MCP servers** as agents:

| Agent | Server Directory | Main Handler |
|-------|------------------|--------------|
| IT Lead | `it-lead-mcp-server` | `ExtendedItLeadServerHandlers` |
| Implementation Engineer | `mcp-vibe-coding-agent` | `VibeCodingAgentHandlers` |
| Requirements Engineer | `requirements-engineer-mcp-server` | `McpServerHandlers` |
| DevOps Engineer | `devops-release-engineer-mcp-server` | `McpServerHandlers` |
| Code Reviewer | `mcp-codereview-agent` | - |
| QA/Test Engineer | - | - |
| Security Engineer | - | - |
| Architect | - | - |

Each agent is a separate process that:
1. Registers with the MCP registry (port 3031)
2. Exposes MCP endpoints for tools/resources/prompts
3. Communicates with other agents via MCP

## AgentGitHelper API

### Initialization

```python
from it_lead_mcp_server.utils.agent_git_helper import AgentGitHelper, get_agent_git_helper

# Method 1: Create instance directly
helper = AgentGitHelper(
    repo_url="ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git",
    repo_path="/var/mcp-results",
    commit_user="mcp-agent",
    commit_email="mcp-agent@localhost",
    branch_prefix="agent/"
)

# Method 2: Use helper function (with caching)
helper = get_agent_git_helper(
    agent_name="implementation-engineer",
    repo_url="ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git"
)
```

### Store Code Result

```python
result = helper.store_code_result(
    task_id="task-123",
    code="def hello():\n    print('Hello World')",
    language="python",
    filename="main",
    metadata={"agent": "implementation-engineer", "tool": "generate_code_from_spec"}
)

# Returns:
# {
#     "success": True,
#     "git_url": "ssh://.../tree/agent/impl/results/task-123/main.py",
#     "file_path": "results/task-123/main.py",
#     "commit_msg": "[agent/impl] Add result for task task-123: main"
# }
```

### Store Document Result

```python
result = helper.store_document_result(
    task_id="task-123",
    content="# Requirements Document\n\n...", 
    document_type="markdown",
    filename="requirements",
    metadata={"agent": "requirements-engineer"}
)
```

### Store Config Result

```python
result = helper.store_config_result(
    task_id="task-123",
    content='{"key": "value"}',
    config_type="json",
    filename="config",
    metadata={"agent": "devops-engineer"}
)
```

## Integration Example

### Implementation Engineer Agent

```python
# agents/implementation_engineer_agent.py
import os
from it_lead_mcp_server.utils.agent_git_helper import get_agent_git_helper

class ImplementationEngineerAgent:
    def __init__(self):
        # Initialize Git helper
        self.git_helper = get_agent_git_helper(
            agent_name="implementation-engineer",
            repo_url=os.environ.get("MCP_GIT_REPO_URL", "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git")
        )
    
    def generate_code_from_spec(self, specifications, programming_language, framework):
        """Generate code from specifications"""
        # ... LLM code generation logic ...
        code = self._generate_code_with_llm(specifications, programming_language, framework)
        
        # Store in Git and return URL
        result = self.git_helper.store_code_result(
            task_id=self.current_task_id,
            code=code,
            language=programming_language,
            filename="generated_code",
            metadata={
                "specifications": specifications,
                "framework": framework
            }
        )
        
        if result["success"]:
            return {
                "status": "success",
                "code_url": result["git_url"],
                "message": "Code generated and stored in Git"
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to store code: {result.get('error')}"
            }
    
    def implement_feature(self, feature_requirements, architectural_guidelines):
        """Implement a feature"""
        # ... LLM implementation logic ...
        code = self._implement_feature_with_llm(feature_requirements, architectural_guidelines)
        
        # Store in Git
        result = self.git_helper.store_code_result(
            task_id=self.current_task_id,
            code=code,
            language="python",
            filename="feature_implementation",
            metadata={
                "feature_requirements": feature_requirements,
                "architectural_guidelines": architectural_guidelines
            }
        )
        
        return {
            "status": "success",
            "implementation_url": result["git_url"],
            "message": "Feature implemented and stored in Git"
        }
```

### Requirements Engineer Agent (`requirements-engineer-mcp-server`)

```python
# requirements-engineer-mcp-server/mcp_std_server/handlers/server_handlers.py
import os
from ..utils.agent_git_helper import get_agent_git_helper

class McpServerHandlers:
    def __init__(self, ...):
        # Initialize Git helper for this agent
        self.git_helper = get_agent_git_helper(
            agent_name="requirements-engineer",
            repo_url=os.environ.get("MCP_GIT_REPO_URL")
        )
        # ... rest of initialization ...

    def analyze_requirements(self, stakeholder_inputs, business_context):
        """Analyze stakeholder requirements"""
        # ... LLM analysis logic ...
        analysis = self._analyze_with_llm(stakeholder_inputs, business_context)

        # Store analysis in Git
        result = self.git_helper.store_document_result(
            task_id=self.current_task_id,
            content=analysis,
            document_type="markdown",
            filename="requirements_analysis",
            metadata={
                "stakeholder_inputs": stakeholder_inputs,
                "business_context": business_context
            }
        )

        return {
            "status": "success",
            "analysis_url": result["git_url"],
            "message": "Requirements analyzed and stored in Git"
        }
```

### DevOps Engineer Agent (`devops-release-engineer-mcp-server`)

```python
# devops-release-engineer-mcp-server/mcp_std_server/handlers/server_handlers.py
import os
from ..utils.agent_git_helper import get_agent_git_helper

class McpServerHandlers:
    def __init__(self, ...):
        # Initialize Git helper for this agent
        self.git_helper = get_agent_git_helper(
            agent_name="devops-engineer",
            repo_url=os.environ.get("MCP_GIT_REPO_URL")
        )
        # ... rest of initialization ...

    def orchestrate_deployments(self, application_artifacts, target_environments):
        """Orchestrate deployments"""
        # ... Deployment logic ...
        config = self._generate_deployment_config(application_artifacts, target_environments)

        # Store deployment config in Git
        result = self.git_helper.store_config_result(
            task_id=self.current_task_id,
            content=config,
            config_type="yaml",
            filename="deployment_config",
            metadata={
                "application_artifacts": application_artifacts,
                "target_environments": target_environments
            }
        )

        return {
            "status": "success",
            "config_url": result["git_url"],
            "message": "Deployment config stored in Git"
        }
```

## Environment Variables

Agents should set these environment variables:

```bash
# Git repository URL
export MCP_GIT_REPO_URL="ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git"

# Optional: SSH key path (if using key-based auth)
export MCP_GIT_SSH_KEY_PATH="/home/mcp/.ssh/id_rsa"

# Optional: Commit user (defaults to "mcp-agent")
export MCP_GIT_COMMIT_USER="mcp-agent"

# Optional: Commit email (defaults to "mcp-agent@localhost")
export MCP_GIT_COMMIT_EMAIL="mcp-agent@localhost"
```

## Branch Naming Convention

Agents push to their own branches:

| Agent | Branch Prefix | Example Branch |
|-------|--------------|----------------|
| Implementation Engineer | `agent/impl/` | `agent/impl` |
| Requirements Engineer | `agent/reqs/` | `agent/reqs` |
| DevOps Engineer | `agent/devops/` | `agent/devops` |
| Test Engineer | `agent/test/` | `agent/test` |
| Security Engineer | `agent/security/` | `agent/security` |
| Architect | `agent/arch/` | `agent/arch` |
| Technical Writer | `agent/docs/` | `agent/docs` |

## Result Format

After Git push, agents return results with Git URL:

```json
{
    "status": "success",
    "code_url": "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git/tree/agent/impl/results/task-123/main.py",
    "message": "Code generated and stored in Git",
    "metadata": {
        "agent": "implementation-engineer",
        "branch": "agent/impl",
        "task_id": "task-123"
    }
}
```

## IT Lead Integration

IT Lead stores the Git URL in task metadata:

```python
def handle_task_assignment(self, task_id, task_description, assignee):
    # ... routing logic ...
    
    # Forward task to agent
    agent_response = self._forward_to_agent(task_id, task_description, assignee)
    
    # Agent returns Git URL in result
    git_url = agent_response.get("code_url") or agent_response.get("git_url")
    
    # Store Git URL in task metadata
    if git_url:
        self.task_storage.update_task_result_reference(
            task_id=task_id,
            storage_ref={
                "storage_type": "git",
                "git_url": git_url,
                "storage_path": git_url
            },
            metadata={"agent": assignee}
        )
```

## Migration Path

### Phase 1: Pilot
1. Update one agent (e.g., Implementation Engineer)
2. Test with real tasks
3. Verify Git push works reliably

### Phase 2: Rollout
1. Update remaining agents
2. Remove ResultRouter (or keep as fallback)
3. Update documentation

### Phase 3: Deprecation
1. Remove ResultRouter
2. Archive old storage module
3. Update tests

## Troubleshooting

### SSH Authentication Failed
```bash
# Test SSH connection
ssh sorokin@192.168.51.187

# Verify SSH key is configured
export GIT_SSH_COMMAND="ssh -i /path/to/id_rsa -o StrictHostKeyChecking=no"
```

### Branch Push Failed
```bash
# Check if branch exists
git branch -a

# Create and push branch manually for testing
git checkout -b agent/impl
git push -u origin agent/impl
```

### Permission Denied
```bash
# Verify Git user permissions on remote repo
ssh sorokin@192.168.51.187 "ls -la /home/sorokin/mcp-results.git/"
```

## FAQ

**Q: Do agents need direct Git access?**  
A: Yes, each agent needs SSH access to the Git repository or HTTPS access with credentials.

**Q: What happens if Git push fails?**  
A: Agent should return error status and optionally fallback to centralized storage.

**Q: Can agents commit to main branch?**  
A: No, agents should use their designated branches. Merge requests should integrate to main.

**Q: How are conflicts handled?**  
A: Agents work on separate branches, minimizing conflicts. Merge requests handle integration.
