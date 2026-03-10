#!/usr/bin/env python3
# Patch for llm_task_planner.py to add logging

# Read the file
with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py', 'r') as f:
    content = f.read()

# Patch 1: Add logging to plan_task_assignment method's LLM call
old_llm_call = '''        # Call LLM
        try:
            response = self.llm_client.generate(prompt, temperature=0.3)
            return self._parse_llm_response(response, task_description, routing_context)
        except Exception as e:
            print(f"Error in LLM task planning: {e}")
            return self._get_fallback_plan(task_description, routing_context)'''

new_llm_call = '''        # Call LLM
        try:
            print(f"📞 Calling LLM for task planning...")
            print(f"   Reason: {llm_reason}")
            print(f"   Prompt length: {len(prompt)} characters")
            response = self.llm_client.generate(prompt, temperature=0.3)
            print(f"✅ LLM response received ({len(response)} chars)")
            print(f"   Response preview: {response[:200]}...")
            return self._parse_llm_response(response, task_description, routing_context)
        except Exception as e:
            print(f"❌ Error in LLM task planning: {e}")
            return self._get_fallback_plan(task_description, routing_context)'''

content = content.replace(old_llm_call, new_llm_call)

# Patch 2: Add logging to _parse_llm_response method
old_parse = '''    def _parse_llm_response(self, response: str, task_description: str,
                           routing_context: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM response and return structured planning result"""
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)

                # Add metadata
                result["planning_method"] = "llm"
                result["task_description"] = task_description
                result["timestamp"] = time.time()

                return result
            else:
                # No JSON found, use fallback
                return self._get_fallback_plan(task_description, routing_context)

        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response JSON: {e}")
            return self._get_fallback_plan(task_description, routing_context)'''

new_parse = '''    def _parse_llm_response(self, response: str, task_description: str,
                           routing_context: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM response and return structured planning result"""
        print(f"📄 Parsing LLM response...")
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                print(f"✅ JSON parsed successfully")
                print(f"   Response keys: {list(result.keys())}")
                print(f"   Response: {json.dumps(result, indent=2)}")

                # Add metadata
                result["planning_method"] = "llm"
                result["task_description"] = task_description
                result["timestamp"] = time.time()

                return result
            else:
                print(f"❌ No JSON found in LLM response")
                # No JSON found, use fallback
                return self._get_fallback_plan(task_description, routing_context)

        except json.JSONDecodeError as e:
            print(f"❌ Error parsing LLM response JSON: {e}")
            return self._get_fallback_plan(task_description, routing_context)'''

content = content.replace(old_parse, new_parse)

# Write the modified content
with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py', 'w') as f:
    f.write(content)

print("✅ Patches applied successfully")
