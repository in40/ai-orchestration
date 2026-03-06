#!/usr/bin/env python3
# Patch for extended_server_handlers.py to add logging

# Read the file
with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/handlers/extended_server_handlers.py', 'r') as f:
    content = f.read()

# Patch 1: Add logging to _execute_assign_task_async
old_execute_async = '''    def _execute_assign_task_async(self, task_id: str, task_description: str,
                                   assignee: str, priority: str, deadline: str,
                                   arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task assignment asynchronously - stores task immediately and returns 'submitted' status"""
        # Store the task in the database with 'submitted' status first
        if self.task_storage:
            print(f"DEBUG: Storing task {task_id} with 'submitted' status (async mode)")
            try:
                success = self.task_storage.store_received_task(
                    task_id=task_id,
                    title=f"Task: {task_id}",
                    description=task_description,
                    submitter="api_user",
                    submitter_type="api",
                    transport_channel="streamable-http",
                    assigned_to=assignee if assignee else "unassigned",
                    priority=priority,
                    deadline=deadline if deadline else None,  # Pass None for empty deadline
                    source_server="internal",
                    metadata={"tool_call": "assign_task", "original_arguments": arguments},
                    status="submitted",
                    status_reason="Task submitted for processing, LLM planning in progress"
                )
                print(f"DEBUG: Task stored with 'submitted' status: {success}")
            except Exception as e:
                print(f"DEBUG: Error storing task with 'submitted' status: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("DEBUG: task_storage is None, cannot store task")

        # Start background thread for LLM planning and forwarding
        threading.Thread(
            target=self._background_task_processing,
            args=(task_id, task_description, assignee),
            daemon=True
        ).start()

        return {
            "result": {
                "task_id": task_id,
                "assigned_to": assignee,
                "priority": priority,
                "deadline": deadline,
                "status": "submitted",
                "message": f"Task '{task_id}' submitted for processing. LLM planning and routing in background."
            }
        }'''

new_execute_async = '''    def _execute_assign_task_async(self, task_id: str, task_description: str,
                                   assignee: str, priority: str, deadline: str,
                                   arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task assignment asynchronously - stores task immediately and returns 'submitted' status"""
        print(f"⏳ _execute_assign_task_async called for task {task_id}")
        print(f"   Task description: {task_description[:100]}...")
        print(f"   Assignee: {assignee}")
        
        # Store the task in the database with 'submitted' status first
        if self.task_storage:
            print(f"💾 Storing task {task_id} with 'submitted' status (async mode)")
            try:
                success = self.task_storage.store_received_task(
                    task_id=task_id,
                    title=f"Task: {task_id}",
                    description=task_description,
                    submitter="api_user",
                    submitter_type="api",
                    transport_channel="streamable-http",
                    assigned_to=assignee if assignee else "unassigned",
                    priority=priority,
                    deadline=deadline if deadline else None,  # Pass None for empty deadline
                    source_server="internal",
                    metadata={"tool_call": "assign_task", "original_arguments": arguments},
                    status="submitted",
                    status_reason="Task submitted for processing, LLM planning in progress"
                )
                print(f"✅ Task stored with 'submitted' status: {success}")
            except Exception as e:
                print(f"❌ Error storing task with 'submitted' status: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("❌ task_storage is None, cannot store task")

        # Start background thread for LLM planning and forwarding
        print(f"🚀 Starting background thread for task {task_id}")
        threading.Thread(
            target=self._background_task_processing,
            args=(task_id, task_description, assignee),
            daemon=True
        ).start()

        return {
            "result": {
                "task_id": task_id,
                "assigned_to": assignee,
                "priority": priority,
                "deadline": deadline,
                "status": "submitted",
                "message": f"Task '{task_id}' submitted for processing. LLM planning and routing in background."
            }
        }'''

content = content.replace(old_execute_async, new_execute_async)

# Patch 2: Add logging to _background_task_processing
old_bg_processing = '''    def _background_task_processing(self, task_id: str, task_description: str, assignee: str):
        """Background thread to run LLM planning and forward task to appropriate agent"""
        try:
            print(f"DEBUG: Background task processing started for {task_id}")

            # Use ThreadPoolExecutor for the blocking LLM call
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    self._run_llm_planning_and_forward,
                    task_id, task_description, assignee
                )
                result = future.result(timeout=300)  # 5 minute timeout for LLM planning

            print(f"DEBUG: Background task processing completed for {task_id}: {result}")

        except Exception as e:
            print(f"ERROR in background task processing for {task_id}: {e}")
            import traceback
            traceback.print_exc()'''

new_bg_processing = '''    def _background_task_processing(self, task_id: str, task_description: str, assignee: str):
        """Background thread to run LLM planning and forward task to appropriate agent"""
        print(f"[thread] _background_task_processing started for {task_id}")
        print(f"   Assignee: {assignee}")
        try:
            # Use ThreadPoolExecutor for the blocking LLM call
            with ThreadPoolExecutor(max_workers=1) as executor:
                print(f"[thread] Submitting _run_llm_planning_and_forward for {task_id}")
                future = executor.submit(
                    self._run_llm_planning_and_forward,
                    task_id, task_description, assignee
                )
                print(f"[thread] Waiting for LLM planning result for {task_id}...")
                result = future.result(timeout=300)  # 5 minute timeout for LLM planning
                print(f"[thread] LLM planning result received for {task_id}")

            print(f"[thread] Background task processing completed for {task_id}: {result}")

        except Exception as e:
            print(f"❌ ERROR in background task processing for {task_id}: {e}")
            import traceback
            traceback.print_exc()'''

content = content.replace(old_bg_processing, new_bg_processing)

# Patch 3: Add logging to _run_llm_planning_and_forward
old_run_planning = '''    def _run_llm_planning_and_forward(self, task_id: str, task_description: str, assignee: str):
        """Run LLM planning and forward task - called from background thread"""
        try:
            if not self.task_assignment_manager:
                print(f"DEBUG: Task assignment manager not available for {task_id}")
                return {"error": "Task assignment manager unavailable"}

            # Run the full assignment process
            assignment_result = self.task_assignment_manager.assign_and_forward_task(
                task_id=task_id,
                task_description=task_description,
                assignee=assignee if assignee else None,
                priority="medium",
                deadline=None,
                metadata={"tool_call": "assign_task_async", "original_arguments": {}, "async_mode": True}
            )

            print(f"DEBUG: LLM planning completed for {task_id}: {assignment_result.get('status', 'unknown')}")
            return assignment_result

        except Exception as e:
            print(f"ERROR in LLM planning for {task_id}: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}'''

new_run_planning = '''    def _run_llm_planning_and_forward(self, task_id: str, task_description: str, assignee: str):
        """Run LLM planning and forward task - called from background thread"""
        print(f"[planning] _run_llm_planning_and_forward started for {task_id}")
        print(f"   Assignee: {assignee}")
        print(f"   Task description: {task_description[:100]}...")
        try:
            if not self.task_assignment_manager:
                print(f"❌ Task assignment manager not available for {task_id}")
                return {"error": "Task assignment manager unavailable"}

            print(f"[planning] Calling assign_and_forward_task for {task_id}")
            # Run the full assignment process
            assignment_result = self.task_assignment_manager.assign_and_forward_task(
                task_id=task_id,
                task_description=task_description,
                assignee=assignee if assignee else None,
                priority="medium",
                deadline=None,
                metadata={"tool_call": "assign_task_async", "original_arguments": {}, "async_mode": True}
            )

            print(f"[planning] assign_and_forward_task completed for {task_id}")
            print(f"   Status: {assignment_result.get('status', 'unknown')}")
            print(f"   Assigned to: {assignment_result.get('assigned_to', 'unknown')}")
            print(f"   Forwarded to agent: {assignment_result.get('forwarded_to_agent', 'unknown')}")
            return assignment_result

        except Exception as e:
            print(f"❌ ERROR in LLM planning for {task_id}: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}'''

content = content.replace(old_run_planning, new_run_planning)

# Write the modified content
with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/handlers/extended_server_handlers.py', 'w') as f:
    f.write(content)

print("✅ Patches applied successfully")
