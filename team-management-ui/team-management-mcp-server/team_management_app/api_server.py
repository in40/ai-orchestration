from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os

# Add the parent directory and the mcp_std_server directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import PostgreSQL-only TaskStorage
from mcp_std_server.utils.task_storage import TaskStorage

app = Flask(__name__, static_folder='webapp')
CORS(app)  # Enable CORS for all routes

# Initialize the task storage with PostgreSQL (mcp_registry database)
task_storage = TaskStorage(
    host="127.0.0.1",
    port=5432,
    database="mcp_registry",
    user="postgres",
    password="postgres"
)

# Serve static files (HTML, CSS, JS) from the webapp directory
@app.route('/')
def serve_index():
    return send_from_directory('webapp', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    # Prevent directory traversal attacks
    if '..' in path or path.startswith('/'):
        from flask import abort
        return abort(404)
    return send_from_directory('webapp', path)

@app.route('/api/team-members', methods=['GET'])
def get_team_members():
    """Get all team members from the MCP registry"""
    try:
        import requests
        import json

        # Query the MCP registry for all registered services
        registry_response = requests.post(
            'http://localhost:3031/mcp',
            json={
                "jsonrpc": "2.0",
                "id": "list_services",
                "method": "registry/list",
                "params": {}
            },
            headers={"Content-Type": "application/json"}
        )

        if registry_response.status_code == 200:
            registry_data = registry_response.json()
            services = registry_data.get('result', {}).get('services', [])

            # Filter out the registry itself and get only AI agents
            ai_agents = []
            for service in services:
                service_id = service.get('id', '')
                service_name = service.get('name', '')
                service_desc = service.get('description', '')

                # Skip the registry service itself
                if 'registry' in service_id.lower() or 'registry' in service_name.lower():
                    continue

                # Identify AI agents by checking if they represent specialized team roles
                service_name_lower = service_name.lower()
                is_ai_agent = (
                    'it lead' in service_name_lower or
                    ('requirement' in service_name_lower and 'engineer' in service_name_lower) or
                    ('implementation' in service_name_lower and 'engineer' in service_name_lower) or
                    ('software' in service_name_lower and 'architect' in service_name_lower) or
                    ('code' in service_name_lower and 'review' in service_name_lower) or
                    'qa' in service_name_lower or
                    ('test' in service_name_lower and 'engineer' in service_name_lower) or
                    ('security' in service_name_lower and 'engineer' in service_name_lower) or
                    'devops' in service_name_lower or
                    ('release' in service_name_lower and 'engineer' in service_name_lower) or
                    ('technical' in service_name_lower and 'writer' in service_name_lower) or
                    'team management' in service_name_lower
                )

                # Exclude infrastructure services
                is_not_infrastructure = (
                    'registry' not in service_id.lower() and
                    'MCP Service Registry' not in service_name
                )

                if is_ai_agent and is_not_infrastructure:

                    agent = {
                        'id': service.get('id', ''),
                        'name': service.get('name', 'Unknown Agent'),
                        'email': f"{service.get('id', 'unknown')}@mcp.local",
                        'role': extract_role_from_service_name(service.get('name', '')),
                        'skills': extract_skills_from_capabilities(service.get('capabilities', {})),
                        'availability': 'online',
                        'description': service.get('description', ''),
                        'endpoint': service.get('endpoint', ''),
                        'capabilities': service.get('capabilities', {}),
                        'registered_at': service.get('registered_at'),
                        'last_seen': service.get('last_seen')
                    }
                    ai_agents.append(agent)

            return jsonify(ai_agents)
        else:
            return jsonify([]), 500

    except Exception as e:
        print(f"Error fetching team members from registry: {e}")
        return jsonify([]), 500

def extract_role_from_service_name(service_name):
    """Extract role from service name"""
    if 'IT Lead' in service_name:
        return 'IT Lead Agent'
    elif 'Requirement' in service_name or 'Requirement Engineer' in service_name:
        return 'Requirement Engineer Agent'
    elif 'Implementation' in service_name or 'Implementation Engineer' in service_name:
        return 'Implementation Engineer Agent'
    elif 'Software Architect' in service_name:
        return 'Software Architect Agent'
    elif 'Code Review' in service_name or 'Code Reviewer' in service_name:
        return 'Code Reviewer Agent'
    elif 'QA' in service_name or 'Test' in service_name:
        return 'QA/Test Engineer Agent'
    elif 'Security' in service_name:
        return 'Security Engineer Agent'
    elif 'DevOps' in service_name or 'Release' in service_name:
        return 'DevOps/Release Engineer Agent'
    elif 'Technical Writer' in service_name:
        return 'Technical Writer Agent'
    else:
        return 'AI Agent'

def extract_skills_from_capabilities(capabilities):
    """Extract skills from agent capabilities"""
    skills = []
    if 'tools' in capabilities and isinstance(capabilities['tools'], list):
        skills.extend(capabilities['tools'][:5])
    if len(skills) == 0:
        skills = ['MCP Communication']
    return skills

@app.route('/api/team-members/<member_id>', methods=['GET'])
def get_team_member(member_id):
    """Get a specific team member"""
    member = task_storage.get_team_member(member_id)
    if member:
        return jsonify(member)
    else:
        return jsonify({'error': 'Member not found'}), 404

@app.route('/api/team-members', methods=['POST'])
def create_team_member():
    """Create a new team member"""
    data = request.json
    member = task_storage.create_team_member(data)
    return jsonify(member), 201

@app.route('/api/team-members/<member_id>', methods=['PUT'])
def update_team_member(member_id):
    """Update a team member"""
    data = request.json
    updated_member = task_storage.update_team_member(member_id, data)
    if updated_member:
        return jsonify(updated_member)
    else:
        return jsonify({'error': 'Member not found'}), 404

@app.route('/api/team-members/<member_id>', methods=['DELETE'])
def delete_team_member(member_id):
    """Delete a team member"""
    return jsonify({'error': 'Not implemented'}), 501

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks from PostgreSQL task_registry with deployment info from task_deployments"""
    filters = {}
    if request.args.get('assignee_id'):
        filters['assigned_to'] = request.args.get('assignee_id')
    if request.args.get('status'):
        filters['status'] = request.args.get('status')
    if request.args.get('priority'):
        filters['priority'] = request.args.get('priority')

    tasks = task_storage.list_tasks(filters)
    return jsonify(tasks)

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """Get a specific task with deployment info"""
    task = task_storage.get_task(task_id)
    if task:
        return jsonify(task)
    else:
        return jsonify({'error': 'Task not found'}), 404

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create a new task"""
    data = request.json
    task = task_storage.create_task(data)
    return jsonify(task), 201

@app.route('/api/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    """Update a task"""
    data = request.json
    updated_task = task_storage.update_task(task_id, data)
    if updated_task:
        return jsonify(updated_task)
    else:
        return jsonify({'error': 'Task not found'}), 404

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task"""
    success = task_storage.delete_task(task_id)
    if success:
        return '', 204
    else:
        return jsonify({'error': 'Task not found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
