#!/usr/bin/env python3
"""
AI Coding Agent Client - Interactive Utility
A user-friendly client for submitting coding tasks to the AI Coding Agent via MCP protocol
"""

import json
import time
import uuid
import requests
from threading import Thread, Event
from queue import Queue
import argparse
import sys
import re
from typing import Dict, Any, Optional


class AICodingAgentClient:
    def __init__(self, agent_url="http://localhost:3050", timeout=60):
        self.agent_url = agent_url.rstrip('/')
        self.timeout = timeout
        self.response_queue = Queue()
        self.stop_event = Event()
        self.session = requests.Session()
        self.sse_thread = None
        self.request_responses = {}  # Store responses by request ID
        self.pending_requests = {}   # Track pending requests
        self.sse_connected = Event()  # Event to signal when SSE is connected
        self.session_id = None  # Store the session ID from the endpoint event

    def start_sse_listener(self):
        """Start listening to SSE stream in a separate thread"""
        def listen():
            try:
                # Open SSE connection
                sse_url = f"{self.agent_url}/sse"
                print("🔌 Establishing connection to AI Coding Agent...")

                response = self.session.get(sse_url, stream=True, timeout=self.timeout)

                print("✅ Connected to AI Coding Agent")
                # Signal that we're connected
                self.sse_connected.set()

                for line in response.iter_lines(decode_unicode=True):
                    if self.stop_event.is_set():
                        break

                    line = line.strip()

                    # Handle endpoint event which contains session ID
                    if line.startswith("event: endpoint"):
                        # Look for the next data line which contains the session ID
                        continue
                    elif line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        try:
                            json_data = json.loads(data)

                            # Check if this is an endpoint event (contains session ID)
                            if json_data.get('event') == 'endpoint':
                                session_uri = json_data.get('uri', '')
                                # Extract session ID from the endpoint data if present
                                if 'sessionId' in json_data:
                                    self.session_id = json_data['sessionId']
                                    print(f"🔑 Session established: {self.session_id}")

                            # Check if this is a response to one of our requests
                            req_id = json_data.get('id')
                            if req_id and req_id in self.pending_requests:
                                print(f"📥 Received response for request {req_id}")
                                self.request_responses[req_id] = json_data
                                # Remove from pending requests
                                del self.pending_requests[req_id]

                            # Also put in queue for general processing
                            self.response_queue.put(json_data)
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                if not self.stop_event.is_set():
                    print(f"❌ Error in SSE listener: {e}")
                    self.sse_connected.set()  # Set the event to unblock the main thread in case of error

        self.sse_thread = Thread(target=listen, daemon=True)
        self.sse_thread.start()
        return self.sse_thread

    def send_request(self, method, params=None, request_id=None):
        """Send a request to the AI Coding Agent"""
        if request_id is None:
            request_id = str(uuid.uuid4())

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }

        send_url = f"{self.agent_url}/send"

        # Prepare headers with session ID if available
        headers = {"Content-Type": "application/json"}
        if self.session_id:
            headers["X-MCP-Session-ID"] = self.session_id

        try:
            print(f"📤 Submitting task to AI Coding Agent (ID: {request_id})")
            response = self.session.post(send_url, json=payload, headers=headers, timeout=self.timeout)
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "received":
                    print(f"✅ Task submitted successfully (ID: {request_id})")
                    # Mark this request as pending
                    self.pending_requests[request_id] = {
                        'method': method,
                        'timestamp': time.time()
                    }
                    return request_id
                else:
                    print(f"Response received immediately: {result}")
                    return result
            else:
                print(f"❌ Error submitting task: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error submitting task: {e}")
            return None

    def wait_for_response(self, request_id, timeout=None):
        """Wait for a specific response by ID"""
        if timeout is None:
            timeout = self.timeout
        start_time = time.time()
        print("⏳ Processing your coding task...")

        while time.time() - start_time < timeout:
            if request_id in self.request_responses:
                return self.request_responses[request_id]

            # Show progress indicator
            elapsed = int(time.time() - start_time)
            dots = '.' * ((elapsed % 3) + 1)
            sys.stdout.write(f"\r⏳ Processing{dots} ({elapsed}s elapsed)")
            sys.stdout.flush()
            time.sleep(0.5)

        print("\n⏰ Timeout waiting for response")
        return None

    def wait_for_sse_connection(self, timeout=None):
        """Wait for SSE connection to be established"""
        if timeout is None:
            timeout = self.timeout
        print("⏳ Establishing secure connection...")
        return self.sse_connected.wait(timeout=timeout)

    def execute_coding_task(self, task_description: str, context: str = "", file_path: str = ""):
        """Submit a coding task to the AI Coding Agent"""
        print("🚀 Starting AI Coding Agent Client")
        print("="*60)

        # Start SSE listener FIRST - this is the MCP way
        listener_thread = self.start_sse_listener()

        # Wait for SSE connection to be established
        if not self.wait_for_sse_connection():
            print("❌ Timeout waiting for connection to AI Coding Agent")
            self.stop_event.set()
            return None

        # Small delay to ensure connection is fully ready
        time.sleep(0.2)

        # Prepare parameters for the coding task
        params = {
            "task_description": task_description,
            "context": context,
            "file_path": file_path
        }

        # Send execute_coding_task request
        request_id = str(uuid.uuid4())
        print(f"📝 Task: {task_description[:50]}{'...' if len(task_description) > 50 else ''}")

        req_id = self.send_request("tools/call", {
            "name": "execute_coding_task",
            "arguments": params
        }, request_id)
        
        if not req_id:
            print("❌ Failed to submit coding task")
            self.stop_event.set()
            return None

        # Wait for response
        print("\n🤖 AI Coding Agent is working on your task...")
        response = self.wait_for_response(request_id, self.timeout)

        # Stop the SSE listener
        self.stop_event.set()

        if response:
            return response
        else:
            print("❌ No response received from AI Coding Agent within timeout period")
            # Print any pending requests for debugging
            if self.pending_requests:
                print(f"Still waiting for responses to: {list(self.pending_requests.keys())}")
            return None

    def generate_code_solution(self, requirements: str, language: str = "python", constraints: str = ""):
        """Generate a code solution based on requirements"""
        print("🚀 Starting AI Coding Agent Client")
        print("="*60)

        # Start SSE listener FIRST
        listener_thread = self.start_sse_listener()

        # Wait for SSE connection to be established
        if not self.wait_for_sse_connection():
            print("❌ Timeout waiting for connection to AI Coding Agent")
            self.stop_event.set()
            return None

        # Small delay to ensure connection is fully ready
        time.sleep(0.2)

        # Prepare parameters for the code generation
        params = {
            "requirements": requirements,
            "language": language,
            "constraints": constraints
        }

        # Send generate_code_solution request
        request_id = str(uuid.uuid4())
        print(f"📝 Requirements: {requirements[:50]}{'...' if len(requirements) > 50 else ''}")

        req_id = self.send_request("tools/call", {
            "name": "generate_code_solution",
            "arguments": params
        }, request_id)
        
        if not req_id:
            print("❌ Failed to submit code generation request")
            self.stop_event.set()
            return None

        # Wait for response
        print("\n🤖 AI Coding Agent is generating your solution...")
        response = self.wait_for_response(request_id, self.timeout)

        # Stop the SSE listener
        self.stop_event.set()

        if response:
            return response
        else:
            print("❌ No response received from AI Coding Agent within timeout period")
            return None

    def review_code(self, code: str, review_criteria: str = "general quality, efficiency, best practices"):
        """Review code for quality and best practices"""
        print("🚀 Starting AI Coding Agent Client")
        print("="*60)

        # Start SSE listener FIRST
        listener_thread = self.start_sse_listener()

        # Wait for SSE connection to be established
        if not self.wait_for_sse_connection():
            print("❌ Timeout waiting for connection to AI Coding Agent")
            self.stop_event.set()
            return None

        # Small delay to ensure connection is fully ready
        time.sleep(0.2)

        # Prepare parameters for the code review
        params = {
            "code": code,
            "review_criteria": review_criteria
        }

        # Send review_code request
        request_id = str(uuid.uuid4())
        print(f"🔍 Review criteria: {review_criteria}")

        req_id = self.send_request("tools/call", {
            "name": "review_code",
            "arguments": params
        }, request_id)
        
        if not req_id:
            print("❌ Failed to submit code review request")
            self.stop_event.set()
            return None

        # Wait for response
        print("\n🤖 AI Coding Agent is reviewing your code...")
        response = self.wait_for_response(request_id, self.timeout)

        # Stop the SSE listener
        self.stop_event.set()

        if response:
            return response
        else:
            print("❌ No response received from AI Coding Agent within timeout period")
            return None

    def check_health(self):
        """Check the health of the AI Coding Agent"""
        # Start SSE listener FIRST
        listener_thread = self.start_sse_listener()

        # Wait for SSE connection to be established
        if not self.wait_for_sse_connection():
            print("❌ Timeout waiting for connection to AI Coding Agent")
            self.stop_event.set()
            return None

        # Small delay to ensure connection is fully ready
        time.sleep(0.2)

        # Send health check request
        request_id = str(uuid.uuid4())
        req_id = self.send_request("tools/call", {
            "name": "health_check",
            "arguments": {"detailed": True}
        }, request_id)
        
        if not req_id:
            print("❌ Failed to submit health check request")
            self.stop_event.set()
            return None

        # Wait for response
        response = self.wait_for_response(request_id, self.timeout)

        # Stop the SSE listener
        self.stop_event.set()

        return response

    def close(self):
        """Close the client connection"""
        self.stop_event.set()
        if self.session:
            self.session.close()


def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f" {' '*((60-len(title))//2)}{title}")
    print("="*60)


def print_success_box(message: str):
    """Print a success message in a box"""
    lines = message.split('\n')
    max_len = max(len(line) for line in lines)
    
    print("┌" + "─" * (max_len + 2) + "┐")
    for line in lines:
        print(f"│ {line:<{max_len}} │")
    print("└" + "─" * (max_len + 2) + "┘")


def print_error_box(message: str):
    """Print an error message in a box"""
    lines = message.split('\n')
    max_len = max(len(line) for line in lines)
    
    print("┌" + "─" * (max_len + 2) + "┐")
    for line in lines:
        print(f"│ {line:<{max_len}} │")
    print("└" + "─" * (max_len + 2) + "┘")


def main():
    parser = argparse.ArgumentParser(
        description='AI Coding Agent Client - Submit coding tasks to the AI Coding Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --task "Create a Python function to calculate factorial"
  %(prog)s --task "Fix the bug in this code" --context "The function crashes when input is negative" --code "..."
  %(prog)s --generate "Build a REST API with Flask" --language python
  %(prog)s --review "def hello(): print('Hello World')" --criteria "best practices"
        """
    )
    parser.add_argument('--agent-url', default='http://localhost:3050',
                        help='AI Coding Agent URL (default: http://localhost:3050)')
    parser.add_argument('--task', 
                        help='Submit a coding task to the AI agent')
    parser.add_argument('--context',
                        help='Additional context for the coding task')
    parser.add_argument('--file-path',
                        help='Path to file if the task involves modifying an existing file')
    parser.add_argument('--generate',
                        help='Generate code based on requirements')
    parser.add_argument('--language', default='python',
                        help='Programming language for code generation (default: python)')
    parser.add_argument('--constraints',
                        help='Constraints for code generation')
    parser.add_argument('--review',
                        help='Review code for quality and best practices')
    parser.add_argument('--criteria',
                        help='Review criteria (default: general quality, efficiency, best practices)')
    parser.add_argument('--health', action='store_true',
                        help='Check the health of the AI Coding Agent')
    parser.add_argument('--timeout', type=int, default=60,
                        help='Timeout in seconds (default: 60)')

    args = parser.parse_args()

    client = AICodingAgentClient(args.agent_url, args.timeout)

    try:
        if args.health:
            # Check health
            print_header("AI CODING AGENT HEALTH CHECK")
            response = client.check_health()
            
            if response and 'result' in response:
                result = response['result']
                status = result.get('status', 'unknown')
                
                if status == 'healthy':
                    print_success_box("✅ AI Coding Agent is healthy!\nStatus: ONLINE\nModel: " + result.get('llm_connection', {}).get('model', 'Unknown'))
                else:
                    print_error_box("❌ AI Coding Agent is unhealthy!\nStatus: OFFLINE")
                    
                if 'detailed_info' in result:
                    detailed = result['detailed_info']
                    print(f"\n📊 Detailed Info:")
                    print(f"   Uptime: {detailed.get('uptime_seconds', 0):.1f}s")
                    print(f"   CPU: {detailed.get('cpu_percent', 0)}%")
                    print(f"   Memory: {detailed.get('memory_percent', 0)}%")
            else:
                print_error_box("❌ Could not get health status from AI Coding Agent")
        
        elif args.task:
            # Execute a coding task
            print_header("EXECUTE CODING TASK")
            response = client.execute_coding_task(args.task, args.context or "", args.file_path or "")

            if response:
                print(f"DEBUG: Full response received: {response}")  # Debug line
                if 'result' in response:
                    result = response['result']
                    if result.get('task_completed'):
                        print_header("TASK COMPLETED SUCCESSFULLY")
                        print(result.get('solution', 'No solution provided'))
                        print_success_box("✅ Task completed successfully!")
                    else:
                        print_error_box(f"❌ Task failed:\n{result.get('error', 'Unknown error')}")
                elif 'error' in response:
                    print_error_box(f"❌ Server error:\n{response['error']}")
                else:
                    print_error_box(f"❌ Unexpected response format:\n{response}")
            else:
                print_error_box("❌ No response received from AI Coding Agent")
        
        elif args.generate:
            # Generate code solution
            print_header("GENERATE CODE SOLUTION")
            response = client.generate_code_solution(args.generate, args.language, args.constraints or "")

            if response:
                print(f"DEBUG: Full response received: {response}")  # Debug line
                if 'result' in response:
                    result = response['result']
                    if result.get('solution_generated'):
                        print_header("CODE GENERATION COMPLETED")
                        print(result.get('code', 'No code provided'))
                        print_success_box("✅ Code generation completed successfully!")
                    else:
                        print_error_box(f"❌ Code generation failed:\n{result.get('error', 'Unknown error')}")
                elif 'error' in response:
                    print_error_box(f"❌ Server error:\n{response['error']}")
                else:
                    print_error_box(f"❌ Unexpected response format:\n{response}")
            else:
                print_error_box("❌ No response received from AI Coding Agent")
        
        elif args.review:
            # Review code
            print_header("REVIEW CODE")
            response = client.review_code(args.review, args.criteria or "general quality, efficiency, best practices")

            if response:
                print(f"DEBUG: Full response received: {response}")  # Debug line
                if 'result' in response:
                    result = response['result']
                    if result.get('review_completed'):
                        print_header("CODE REVIEW COMPLETED")
                        print(result.get('feedback', 'No feedback provided'))
                        print_success_box("✅ Code review completed successfully!")
                    else:
                        print_error_box(f"❌ Code review failed:\n{result.get('error', 'Unknown error')}")
                elif 'error' in response:
                    print_error_box(f"❌ Server error:\n{response['error']}")
                else:
                    print_error_box(f"❌ Unexpected response format:\n{response}")
            else:
                print_error_box("❌ No response received from AI Coding Agent")
        
        else:
            # Interactive mode
            print_header("AI CODING AGENT CLIENT")
            print("Welcome to the AI Coding Agent Client!")
            print("Choose an option:")
            print("1. Submit a coding task")
            print("2. Generate code from requirements")
            print("3. Review existing code")
            print("4. Check AI Coding Agent health")
            print("5. Exit")
            
            while True:
                try:
                    choice = input("\nEnter your choice (1-5): ").strip()
                    
                    if choice == '1':
                        task = input("\nEnter your coding task: ").strip()
                        if not task:
                            print("❌ Task cannot be empty!")
                            continue
                            
                        context = input("Enter additional context (optional): ").strip()
                        file_path = input("Enter file path (optional): ").strip()
                        
                        print_header("EXECUTE CODING TASK")
                        response = client.execute_coding_task(task, context, file_path)
                        
                        if response and 'result' in response:
                            result = response['result']
                            if result.get('task_completed'):
                                print_header("TASK COMPLETED SUCCESSFULLY")
                                print(result.get('solution', 'No solution provided'))
                                print_success_box("✅ Task completed successfully!")
                            else:
                                print_error_box(f"❌ Task failed:\n{result.get('error', 'Unknown error')}")
                        else:
                            print_error_box("❌ No response received from AI Coding Agent")
                    
                    elif choice == '2':
                        requirements = input("\nEnter code requirements: ").strip()
                        if not requirements:
                            print("❌ Requirements cannot be empty!")
                            continue
                            
                        language = input("Enter programming language (default: python): ").strip() or "python"
                        constraints = input("Enter constraints (optional): ").strip()
                        
                        print_header("GENERATE CODE SOLUTION")
                        response = client.generate_code_solution(requirements, language, constraints)
                        
                        if response and 'result' in response:
                            result = response['result']
                            if result.get('solution_generated'):
                                print_header("CODE GENERATION COMPLETED")
                                print(result.get('code', 'No code provided'))
                                print_success_box("✅ Code generation completed successfully!")
                            else:
                                print_error_box(f"❌ Code generation failed:\n{result.get('error', 'Unknown error')}")
                        else:
                            print_error_box("❌ No response received from AI Coding Agent")
                    
                    elif choice == '3':
                        code = input("\nEnter code to review: ").strip()
                        if not code:
                            print("❌ Code cannot be empty!")
                            continue
                            
                        criteria = input("Enter review criteria (default: general quality, efficiency, best practices): ").strip()
                        if not criteria:
                            criteria = "general quality, efficiency, best practices"
                        
                        print_header("REVIEW CODE")
                        response = client.review_code(code, criteria)
                        
                        if response and 'result' in response:
                            result = response['result']
                            if result.get('review_completed'):
                                print_header("CODE REVIEW COMPLETED")
                                print(result.get('feedback', 'No feedback provided'))
                                print_success_box("✅ Code review completed successfully!")
                            else:
                                print_error_box(f"❌ Code review failed:\n{result.get('error', 'Unknown error')}")
                        else:
                            print_error_box("❌ No response received from AI Coding Agent")
                    
                    elif choice == '4':
                        print_header("AI CODING AGENT HEALTH CHECK")
                        response = client.check_health()
                        
                        if response and 'result' in response:
                            result = response['result']
                            status = result.get('status', 'unknown')
                            
                            if status == 'healthy':
                                print_success_box("✅ AI Coding Agent is healthy!\nStatus: ONLINE\nModel: " + result.get('llm_connection', {}).get('model', 'Unknown'))
                            else:
                                print_error_box("❌ AI Coding Agent is unhealthy!\nStatus: OFFLINE")
                                
                            if 'detailed_info' in result:
                                detailed = result['detailed_info']
                                print(f"\n📊 Detailed Info:")
                                print(f"   Uptime: {detailed.get('uptime_seconds', 0):.1f}s")
                                print(f"   CPU: {detailed.get('cpu_percent', 0)}%")
                                print(f"   Memory: {detailed.get('memory_percent', 0)}%")
                        else:
                            print_error_box("❌ Could not get health status from AI Coding Agent")
                    
                    elif choice == '5':
                        print("\n👋 Thank you for using AI Coding Agent Client!")
                        break
                    
                    else:
                        print("❌ Invalid choice. Please enter 1-5.")
                        
                except KeyboardInterrupt:
                    print("\n\n👋 Thank you for using AI Coding Agent Client!")
                    break
                except Exception as e:
                    print(f"\n❌ Error: {e}")
                    import traceback
                    traceback.print_exc()

    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


if __name__ == "__main__":
    main()