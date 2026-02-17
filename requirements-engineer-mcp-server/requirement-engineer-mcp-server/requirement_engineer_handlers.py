"""
Requirement Engineer Server Handlers for MCP Server
Implements all requirement engineering tools, resources, and prompts
"""
import time
import json
import requests
from typing import Dict, Any, List, Optional
from mcp_std_server.utils.json_rpc import JsonRpcHandler, JsonRpcMessage
from mcp_std_server.handlers.server_handlers import McpServerHandlers
from mcp_std_server.utils.task_storage import TaskStorage


class RequirementEngineerHandlers(McpServerHandlers):
    """Handles requirement engineering specific MCP server methods"""

    def __init__(self, enable_registry: bool = False, use_postgres: bool = False,
                 postgres_config: Optional[Dict[str, Any]] = None, client_handlers=None):
        # Initialize the parent class
        super().__init__(enable_registry, use_postgres, postgres_config, client_handlers)
        
        # Clear default example tools and replace with requirement engineering tools
        self.tools = []
        self.resources = []
        self.prompts = []
        
        # Add requirement engineering tools
        self._add_requirement_engineering_tools()
        
        # Initialize task storage for tracking requirements tasks
        if use_postgres and postgres_config:
            self.task_storage = TaskStorage(use_postgres=True, postgres_config=postgres_config)
        else:
            self.task_storage = TaskStorage(use_postgres=False)

    def _add_requirement_engineering_tools(self):
        """Add requirement engineering specific tools"""
        requirement_engineering_tools = [
            {
                "name": "analyze_requirements",
                "description": "Analyze incoming stakeholder inputs and extract structured requirements",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "stakeholder_inputs": {"type": "string", "description": "Raw stakeholder inputs (interviews, documents, etc.)"},
                        "business_context": {"type": "string", "description": "Business context and constraints"},
                        "previous_requirements": {"type": "array", "items": {"type": "object"}, "description": "Previous requirements for reference"}
                    },
                    "required": ["stakeholder_inputs", "business_context"]
                }
            },
            {
                "name": "resolve_ambiguity",
                "description": "Identify ambiguous requirements and generate clarification requests",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "requirements": {"type": "array", "items": {"type": "object"}, "description": "Requirements to analyze for ambiguity"},
                        "stakeholder_context": {"type": "string", "description": "Context about stakeholders involved"},
                        "clarification_history": {"type": "array", "items": {"type": "object"}, "description": "Previous clarification attempts"}
                    },
                    "required": ["requirements"]
                }
            },
            {
                "name": "translate_business_to_technical",
                "description": "Convert business requirements to technical specifications",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "business_requirements": {"type": "array", "items": {"type": "object"}, "description": "Business requirements to translate"},
                        "technical_constraints": {"type": "array", "items": {"type": "string"}, "description": "Technical constraints and limitations"},
                        "system_context": {"type": "string", "description": "System context and architecture constraints"}
                    },
                    "required": ["business_requirements", "technical_constraints"]
                }
            },
            {
                "name": "generate_traceability_matrix",
                "description": "Create and maintain requirement-to-implementation links",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "requirements": {"type": "array", "items": {"type": "object"}, "description": "Requirements to include in matrix"},
                        "design_elements": {"type": "array", "items": {"type": "object"}, "description": "Design elements linked to requirements"},
                        "code_modules": {"type": "array", "items": {"type": "object"}, "description": "Code modules implementing requirements"},
                        "test_cases": {"type": "array", "items": {"type": "object"}, "description": "Test cases validating requirements"}
                    },
                    "required": ["requirements"]
                }
            },
            {
                "name": "identify_edge_cases",
                "description": "Identify non-functional requirements and edge cases",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "functional_requirements": {"type": "array", "items": {"type": "object"}, "description": "Functional requirements to analyze"},
                        "domain_context": {"type": "string", "description": "Domain-specific context for edge case identification"},
                        "security_requirements": {"type": "array", "items": {"type": "string"}, "description": "Security requirements to consider"}
                    },
                    "required": ["functional_requirements"]
                }
            }
        ]
        
        # Extend the tools list with requirement engineering tools
        self.tools.extend(requirement_engineering_tools)
        
        # Add requirement engineering resources
        requirement_resources = [
            {
                "uri": "requirements://resource/specifications",
                "name": "Requirements Specifications",
                "description": "Structured requirements documents and specifications"
            },
            {
                "uri": "requirements://resource/traceability-matrix",
                "name": "Traceability Matrix",
                "description": "Matrix linking requirements to design, code, and tests"
            },
            {
                "uri": "requirements://resource/ambiguity-log",
                "name": "Ambiguity Log",
                "description": "Log of identified ambiguities and their resolution status"
            }
        ]
        
        self.resources.extend(requirement_resources)
        
        # Add requirement engineering prompts
        requirement_prompts = [
            {
                "name": "requirements_analysis_prompt",
                "description": "Prompt for analyzing requirements and extracting structured information",
                "arguments": [
                    {
                        "name": "stakeholder_inputs",
                        "type": "string",
                        "description": "Raw stakeholder inputs to analyze"
                    },
                    {
                        "name": "business_context",
                        "type": "string",
                        "description": "Business context for the requirements"
                    }
                ]
            },
            {
                "name": "ambiguity_identification_prompt",
                "description": "Prompt for identifying ambiguous requirements",
                "arguments": [
                    {
                        "name": "requirements",
                        "type": "string",
                        "description": "Requirements to analyze for ambiguity"
                    }
                ]
            },
            {
                "name": "business_to_technical_translation_prompt",
                "description": "Prompt for translating business requirements to technical specifications",
                "arguments": [
                    {
                        "name": "business_requirements",
                        "type": "string",
                        "description": "Business requirements to translate"
                    },
                    {
                        "name": "technical_constraints",
                        "type": "string",
                        "description": "Technical constraints to consider"
                    }
                ]
            }
        ]
        
        self.prompts.extend(requirement_prompts)

    def _execute_tool(self, tool: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific requirement engineering tool with given arguments"""
        tool_name = tool["name"]

        # Create a task record for tracking
        task_id = f"req-eng-{int(time.time())}-{tool_name}"
        self.task_storage.create_task(task_id, tool_name, arguments, "started")

        try:
            # Handle requirement engineering tools
            if tool_name == "analyze_requirements":
                result = self._analyze_requirements(arguments)
            elif tool_name == "resolve_ambiguity":
                result = self._resolve_ambiguity(arguments)
            elif tool_name == "translate_business_to_technical":
                result = self._translate_business_to_technical(arguments)
            elif tool_name == "generate_traceability_matrix":
                result = self._generate_traceability_matrix(arguments)
            elif tool_name == "identify_edge_cases":
                result = self._identify_edge_cases(arguments)
            else:
                # For registry tools, call parent method
                result = super()._execute_tool(tool, arguments)

            # Update task status to completed
            self.task_storage.update_task_status(task_id, "completed", result)
            
            return result
            
        except Exception as e:
            # Update task status to failed
            error_msg = str(e)
            self.task_storage.update_task_status(task_id, "failed", {"error": error_msg})
            raise e

    def _analyze_requirements(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze requirements using LLM"""
        stakeholder_inputs = arguments.get("stakeholder_inputs", "")
        business_context = arguments.get("business_context", "")
        previous_requirements = arguments.get("previous_requirements", [])
        
        # Call the LLM to analyze requirements
        llm_result = self._call_llm_for_requirements_analysis(stakeholder_inputs, business_context, previous_requirements)
        
        # Store the results in the database
        if isinstance(llm_result, dict) and "functional_requirements" in llm_result:
            # Store functional requirements
            for req in llm_result.get("functional_requirements", []):
                req_id = req.get("id", f"FUNC-{int(time.time())}")
                self.task_storage.store_requirement_specification(
                    requirement_id=req_id,
                    description=req.get("description", ""),
                    status=req.get("status", "draft"),
                    priority=req.get("priority", "medium"),
                    category=req.get("category", "functional")
                )
            
            # Store non-functional requirements
            for req in llm_result.get("non_functional_requirements", []):
                req_id = req.get("id", f"NFR-{int(time.time())}")
                self.task_storage.store_requirement_specification(
                    requirement_id=req_id,
                    description=req.get("description", ""),
                    status=req.get("status", "draft"),
                    priority=req.get("priority", "medium"),
                    category=req.get("category", "non-functional")
                )
            
            # Store ambiguities
            for amb in llm_result.get("ambiguities", []):
                amb_id = amb.get("id", f"AMB-{int(time.time())}")
                self.task_storage.store_ambiguity(
                    ambiguity_id=amb_id,
                    requirement_id=amb.get("requirement_id", ""),
                    description=amb.get("description", ""),
                    severity=amb.get("severity", "medium"),
                    status=amb.get("status", "open"),
                    resolution=amb.get("resolution", "")
                )
        
        return {
            "structured_requirements": llm_result,
            "analysis_summary": f"Analyzed {len(stakeholder_inputs.split())} words of stakeholder input and identified key requirements"
        }

    def _resolve_ambiguity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve ambiguities in requirements"""
        requirements = arguments.get("requirements", [])
        stakeholder_context = arguments.get("stakeholder_context", "")
        clarification_history = arguments.get("clarification_history", [])
        
        # Call the LLM to identify ambiguities and generate clarifications
        llm_result = self._call_llm_for_ambiguity_resolution(requirements, stakeholder_context, clarification_history)
        
        # Store the results in the database
        if isinstance(llm_result, dict):
            # Store ambiguities
            for amb in llm_result.get("ambiguities", []):
                amb_id = amb.get("id", f"AMB-{int(time.time())}")
                self.task_storage.store_ambiguity(
                    ambiguity_id=amb_id,
                    requirement_id=amb.get("requirement_id", ""),
                    description=amb.get("description", ""),
                    severity=amb.get("severity", "medium"),
                    status=amb.get("status", "open"),
                    resolution=amb.get("resolution", "")
                )
        
        return {
            "identified_ambiguities": llm_result.get("ambiguities", []),
            "clarification_questions": llm_result.get("clarification_questions", []),
            "resolution_suggestions": llm_result.get("resolution_suggestions", [])
        }

    def _translate_business_to_technical(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Translate business requirements to technical specifications"""
        business_requirements = arguments.get("business_requirements", [])
        technical_constraints = arguments.get("technical_constraints", [])
        system_context = arguments.get("system_context", "")
        
        # Call the LLM to translate business to technical
        llm_result = self._call_llm_for_business_to_technical_translation(
            business_requirements, technical_constraints, system_context
        )
        
        # Store the results in the database
        if isinstance(llm_result, dict):
            # Store technical specifications as requirements
            for spec in llm_result.get("technical_specifications", []):
                req_id = spec.get("requirement_id", f"TECH-{int(time.time())}")
                self.task_storage.store_requirement_specification(
                    requirement_id=req_id,
                    description=spec.get("technical_description", ""),
                    status=spec.get("status", "draft"),
                    priority=spec.get("priority", "medium"),
                    category="technical"
                )
        
        return {
            "technical_specifications": llm_result,
            "translation_notes": "Business requirements translated to technical specifications"
        }

    def _generate_traceability_matrix(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate traceability matrix linking requirements to implementation"""
        requirements = arguments.get("requirements", [])
        design_elements = arguments.get("design_elements", [])
        code_modules = arguments.get("code_modules", [])
        test_cases = arguments.get("test_cases", [])
        
        # Create traceability matrix
        matrix = self._create_traceability_matrix(requirements, design_elements, code_modules, test_cases)

        # Store the traceability links in the database
        for entry in matrix.get("matrix_entries", []):
            self.task_storage.store_traceability_link(
                requirement_id=entry.get("requirement_id", ""),
                artifact_type=entry.get("artifact_type", ""),
                artifact_id=entry.get("artifact_id", ""),
                relationship=entry.get("relationship", ""),
                confidence=entry.get("confidence", 0.7)
            )

        return {
            "traceability_matrix": matrix,
            "coverage_stats": self._calculate_coverage_stats(matrix)
        }

    def _identify_edge_cases(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Identify edge cases and non-functional requirements"""
        functional_requirements = arguments.get("functional_requirements", [])
        domain_context = arguments.get("domain_context", "")
        security_requirements = arguments.get("security_requirements", [])
        
        # Call the LLM to identify edge cases
        llm_result = self._call_llm_for_edge_case_identification(
            functional_requirements, domain_context, security_requirements
        )

        # Store the results in the database
        if isinstance(llm_result, dict):
            # Store edge cases as requirements
            for edge_case in llm_result.get("edge_cases", []):
                req_id = edge_case.get("id", f"EDGE-{int(time.time())}")
                self.task_storage.store_requirement_specification(
                    requirement_id=req_id,
                    description=edge_case.get("scenario", ""),
                    status="draft",
                    priority=edge_case.get("priority", "medium"),
                    category="edge_case"
                )
            
            # Store non-functional requirements
            for nfr in llm_result.get("non_functional_requirements", []):
                req_id = nfr.get("id", f"NFR-{int(time.time())}")
                self.task_storage.store_requirement_specification(
                    requirement_id=req_id,
                    description=nfr.get("description", ""),
                    status=nfr.get("status", "draft"),
                    priority=nfr.get("priority", "medium"),
                    category=nfr.get("category", "non-functional")
                )

        return {
            "edge_cases": llm_result.get("edge_cases", []),
            "non_functional_requirements": llm_result.get("non_functional_requirements", []),
            "security_considerations": llm_result.get("security_considerations", [])
        }

    def _call_llm_for_requirements_analysis(self, stakeholder_inputs: str, business_context: str, previous_requirements: List) -> Dict[str, Any]:
        """Call LLM to analyze requirements"""
        # Construct the prompt for requirements analysis
        prompt = f'''
        As a requirements engineer, analyze the following stakeholder inputs and extract structured requirements.

        You MUST respond in valid JSON format with the following structure:
        {{
          "functional_requirements": [
            {{
              "id": "string",
              "description": "string",
              "status": "draft|approved|rejected|implemented",
              "priority": "low|medium|high|critical",
              "category": "string",
              "related_to": ["other_requirement_ids"]
            }}
          ],
          "non_functional_requirements": [
            {{
              "id": "string",
              "description": "string", 
              "status": "draft|approved|rejected|implemented",
              "priority": "low|medium|high|critical",
              "category": "performance|security|usability|reliability|scalability|compatibility",
              "constraints": ["constraint_strings"]
            }}
          ],
          "ambiguities": [
            {{
              "id": "string",
              "requirement_id": "string",
              "description": "string",
              "status": "open|in_review|resolved",
              "notes": "string"
            }}
          ],
          "assumptions": [
            {{
              "id": "string",
              "description": "string",
              "validity_period": "string"
            }}
          ],
          "dependencies": [
            {{
              "from_requirement": "string",
              "to_requirement": "string",
              "type": "depends_on|conflicts_with|related_to"
            }}
          ]
        }}

        Stakeholder Inputs:
        {stakeholder_inputs}

        Business Context:
        {business_context}

        Previous Requirements (for reference):
        {json.dumps(previous_requirements)}
        '''
        
        return self._call_llm(prompt)

    def _call_llm_for_ambiguity_resolution(self, requirements: List, stakeholder_context: str, clarification_history: List) -> Dict[str, Any]:
        """Call LLM to resolve ambiguities"""
        prompt = f'''
        As a requirements engineer, analyze the following requirements for ambiguities and generate clarification questions.

        You MUST respond in valid JSON format with the following structure:
        {{
          "ambiguities": [
            {{
              "id": "string",
              "requirement_id": "string",
              "description": "string",
              "severity": "low|medium|high|critical",
              "status": "open|in_review|resolved|wont_fix",
              "date_identified": "YYYY-MM-DD",
              "date_resolved": "YYYY-MM-DD|null",
              "resolution": "string|null"
            }}
          ],
          "clarification_questions": [
            {{
              "id": "string",
              "requirement_id": "string",
              "question": "string",
              "stakeholder_type": "string",
              "urgency": "low|medium|high"
            }}
          ],
          "resolution_suggestions": [
            {{
              "id": "string",
              "ambiguity_id": "string",
              "suggestion": "string",
              "impact": "low|medium|high"
            }}
          ]
        }}

        Requirements:
        {json.dumps(requirements)}

        Stakeholder Context:
        {stakeholder_context}

        Previous Clarification History:
        {json.dumps(clarification_history)}
        '''
        
        return self._call_llm(prompt)

    def _call_llm_for_business_to_technical_translation(self, business_requirements: List, technical_constraints: List, system_context: str) -> Dict[str, Any]:
        """Call LLM to translate business to technical"""
        prompt = f'''
        As a requirements engineer, translate the following business requirements to technical specifications.

        You MUST respond in valid JSON format with the following structure:
        {{
          "technical_specifications": [
            {{
              "requirement_id": "string",
              "business_requirement_ref": "string",
              "technical_description": "string",
              "components": ["component_names"],
              "technologies": ["technology_names"],
              "implementation_approach": "string",
              "complexity": "low|medium|high|very_high",
              "estimated_effort_days": number
            }}
          ],
          "implementation_considerations": [
            {{
              "requirement_id": "string",
              "consideration_type": "performance|security|scalability|usability|maintainability",
              "description": "string",
              "priority": "low|medium|high"
            }}
          ],
          "technology_recommendations": [
            {{
              "requirement_id": "string",
              "category": "frontend|backend|database|security|monitoring",
              "recommendation": "string",
              "alternatives": ["alternative_tech_options"],
              "justification": "string"
            }}
          ],
          "potential_challenges": [
            {{
              "requirement_id": "string",
              "challenge_type": "technical|architectural|performance|integration|security",
              "description": "string",
              "mitigation_strategy": "string",
              "risk_level": "low|medium|high"
            }}
          ]
        }}

        Business Requirements:
        {json.dumps(business_requirements)}

        Technical Constraints:
        {json.dumps(technical_constraints)}

        System Context:
        {system_context}
        '''
        
        return self._call_llm(prompt)

    def _call_llm_for_edge_case_identification(self, functional_requirements: List, domain_context: str, security_requirements: List) -> Dict[str, Any]:
        """Call LLM to identify edge cases"""
        prompt = f'''
        As a requirements engineer, analyze the following functional requirements to identify edge cases and non-functional requirements.

        You MUST respond in valid JSON format with the following structure:
        {{
          "edge_cases": [
            {{
              "id": "string",
              "requirement_id": "string",
              "scenario": "string",
              "trigger_condition": "string",
              "expected_behavior": "string",
              "priority": "low|medium|high|critical",
              "category": "error_handling|boundary_conditions|concurrency|performance|security|usability"
            }}
          ],
          "non_functional_requirements": [
            {{
              "id": "string",
              "requirement_id": "string",
              "description": "string",
              "category": "performance|security|usability|reliability|scalability|compatibility|maintainability",
              "acceptance_criteria": ["criteria_strings"],
              "priority": "low|medium|high|critical"
            }}
          ],
          "security_considerations": [
            {{
              "id": "string",
              "requirement_id": "string",
              "concern": "string",
              "threat_type": "injection|xss|csrf|privacy|auth|other",
              "mitigation_strategy": "string",
              "risk_level": "low|medium|high|critical"
            }}
          ],
          "error_handling_requirements": [
            {{
              "id": "string",
              "requirement_id": "string",
              "error_type": "validation|system|network|timeout|permission",
              "handling_strategy": "string",
              "fallback_behavior": "string"
            }}
          ]
        }}

        Functional Requirements:
        {json.dumps(functional_requirements)}

        Domain Context:
        {domain_context}

        Security Requirements:
        {json.dumps(security_requirements)}
        '''
        
        return self._call_llm(prompt)

    def _create_traceability_matrix(self, requirements: List, design_elements: List, code_modules: List, test_cases: List) -> Dict[str, Any]:
        """Create traceability matrix"""
        matrix = {
            "requirements_to_design": {},
            "requirements_to_code": {},
            "requirements_to_tests": {},
            "coverage_percentage": 0,
            "matrix_entries": []  # New structured format for storage
        }
        
        # Create mappings between requirements and other elements
        for req in requirements:
            req_id = req.get("id", req.get("name", str(hash(str(req)))))
            matrix["requirements_to_design"][req_id] = []
            matrix["requirements_to_code"][req_id] = []
            matrix["requirements_to_tests"][req_id] = []
            
            # Simple matching based on keywords (in a real implementation, this would be more sophisticated)
            for design_elem in design_elements:
                if self._has_keyword_match(req, design_elem):
                    design_id = design_elem.get("id", design_elem.get("name"))
                    matrix["requirements_to_design"][req_id].append(design_id)
                    # Add to structured entries for storage
                    matrix["matrix_entries"].append({
                        "requirement_id": req_id,
                        "artifact_type": "design",
                        "artifact_id": design_id,
                        "relationship": "specifies_design",
                        "confidence": 0.7  # Default confidence
                    })
                    
            for code_mod in code_modules:
                if self._has_keyword_match(req, code_mod):
                    code_id = code_mod.get("id", code_mod.get("name"))
                    matrix["requirements_to_code"][req_id].append(code_id)
                    # Add to structured entries for storage
                    matrix["matrix_entries"].append({
                        "requirement_id": req_id,
                        "artifact_type": "code",
                        "artifact_id": code_id,
                        "relationship": "implemented_by",
                        "confidence": 0.7
                    })
                    
            for test_case in test_cases:
                if self._has_keyword_match(req, test_case):
                    test_id = test_case.get("id", test_case.get("name"))
                    matrix["requirements_to_tests"][req_id].append(test_id)
                    # Add to structured entries for storage
                    matrix["matrix_entries"].append({
                        "requirement_id": req_id,
                        "artifact_type": "test",
                        "artifact_id": test_id,
                        "relationship": "validated_by",
                        "confidence": 0.7
                    })
        
        # Calculate coverage statistics
        matrix["coverage_stats"] = self._calculate_coverage_stats(matrix)
        
        return matrix

    def _has_keyword_match(self, req: Dict, element: Dict) -> bool:
        """Simple keyword matching between requirement and element"""
        req_text = f"{req.get('name', '')} {req.get('description', '')}".lower()
        elem_text = f"{element.get('name', '')} {element.get('description', '')}".lower()
        
        # Simple keyword overlap check
        req_words = set(req_text.split())
        elem_words = set(elem_text.split())
        common_words = req_words.intersection(elem_words)
        
        # Consider it a match if there's at least one common significant word
        return len(common_words) > 0

    def _calculate_coverage_stats(self, matrix: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate coverage statistics for the traceability matrix"""
        stats = {
            "total_requirements": len(matrix["requirements_to_design"]),
            "requirements_with_design": len([k for k, v in matrix["requirements_to_design"].items() if v]),
            "requirements_with_code": len([k for k, v in matrix["requirements_to_code"].items() if v]),
            "requirements_with_tests": len([k for k, v in matrix["requirements_to_tests"].items() if v])
        }
        
        stats["design_coverage"] = (stats["requirements_with_design"] / stats["total_requirements"]) * 100 if stats["total_requirements"] > 0 else 0
        stats["code_coverage"] = (stats["requirements_with_code"] / stats["total_requirements"]) * 100 if stats["total_requirements"] > 0 else 0
        stats["test_coverage"] = (stats["requirements_with_tests"] / stats["total_requirements"]) * 100 if stats["total_requirements"] > 0 else 0
        
        return stats

    def _extract_json_from_response(self, content: str) -> Dict[str, Any]:
        """
        Extract JSON from LLM response that might contain additional text.
        Looks for JSON between ```json and ``` markers or tries to parse the whole content.
        """
        # Look for JSON between code block markers
        import re
        json_pattern = r'```(?:json)?\s*({.*?})\s*```'
        match = re.search(json_pattern, content, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # If no code blocks found, try to parse the entire content
        # First, try to find a JSON object in the content
        brace_start = content.find('{')
        if brace_start != -1:
            # Find the matching closing brace
            brace_count = 0
            for i, char in enumerate(content[brace_start:], brace_start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_str = content[brace_start:i+1]
                        try:
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            break
        
        # If all parsing attempts fail, return the raw content
        return {"raw_response": content}

    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """
        Call the LLM with the given prompt.
        Uses the LM Studio endpoint as specified in the requirements.
        """
        try:
            # LM Studio endpoint details from the requirements
            url = "http://asus-tus:1234/v1/chat/completions"
            
            # Prepare the payload for the LLM API
            payload = {
                "model": "qwen3-4b",  # From requirements
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2048
            }
            
            # Make the request to the LLM
            response = requests.post(url, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Extract JSON from the response
                return self._extract_json_from_response(content)
            else:
                print(f"LLM API request failed with status {response.status_code}: {response.text}")
                return {"error": f"LLM API request failed: {response.status_code}"}
                
        except Exception as e:
            print(f"Error calling LLM: {str(e)}")
            return {"error": f"Error calling LLM: {str(e)}"}

    def _read_resource(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Read content from a specific requirement engineering resource"""
        # Check if resource is a string (URI) or a dictionary with URI
        if isinstance(resource, str):
            uri = resource
        elif isinstance(resource, dict) and "uri" in resource:
            uri = resource["uri"]
        else:
            # If resource format is unexpected, call parent method
            return super()._read_resource(resource)
        
        if uri == "requirements://resource/specifications":
            # Return actual requirements specifications from the database
            stored_specs = self.task_storage.get_requirement_specifications(limit=100)
            
            specs_content = {
                "title": "Requirements Specifications Document",
                "version": "1.0",
                "generated_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                "functional_requirements": [
                    {
                        "id": spec["requirement_id"],
                        "description": spec["description"],
                        "status": spec["status"],
                        "priority": spec["priority"],
                        "category": spec["category"]
                    }
                    for spec in stored_specs if spec["category"] and "functional" in spec["category"].lower()
                ],
                "non_functional_requirements": [
                    {
                        "id": spec["requirement_id"],
                        "description": spec["description"],
                        "status": spec["status"],
                        "priority": spec["priority"],
                        "category": spec["category"]
                    }
                    for spec in stored_specs if spec["category"] and "non-functional" in spec["category"].lower()
                ],
                "technical_requirements": [
                    {
                        "id": spec["requirement_id"],
                        "description": spec["description"],
                        "status": spec["status"],
                        "priority": spec["priority"],
                        "category": spec["category"]
                    }
                    for spec in stored_specs if spec["category"] and "technical" in spec["category"].lower()
                ],
                "edge_cases": [
                    {
                        "id": spec["requirement_id"],
                        "description": spec["description"],
                        "status": spec["status"],
                        "priority": spec["priority"],
                        "category": spec["category"]
                    }
                    for spec in stored_specs if spec["category"] and "edge_case" in spec["category"].lower()
                ],
                "metadata": {
                    "last_updated": time.time(),
                    "generated_by": "Requirement Engineer MCP Server",
                    "total_requirements": len(stored_specs),
                    "status": "active"
                }
            }
            
            return {
                "contents": [{
                    "uri": uri,
                    "text": json.dumps(specs_content, indent=2)
                }]
            }
        elif uri == "requirements://resource/traceability-matrix":
            # Return actual traceability matrix from the database
            stored_links = self.task_storage.get_traceability_links(limit=100)
            
            matrix_content = {
                "title": "Requirements Traceability Matrix",
                "version": "1.0",
                "generated_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                "matrix": [
                    {
                        "requirement_id": link["requirement_id"],
                        "artifact_type": link["artifact_type"],
                        "artifact_id": link["artifact_id"],
                        "relationship": link["relationship"],
                        "confidence": link["confidence"]
                    }
                    for link in stored_links
                ],
                "coverage_stats": {
                    "total_requirements": len(set(link["requirement_id"] for link in stored_links)),
                    "traced_artifacts": len(stored_links),
                    "coverage_percentage": len(stored_links) * 100 / max(len(set(link["requirement_id"] for link in stored_links)), 1) if stored_links else 0
                },
                "metadata": {
                    "last_updated": time.time(),
                    "generated_by": "Requirement Engineer MCP Server",
                    "status": "active"
                }
            }
            
            return {
                "contents": [{
                    "uri": uri,
                    "text": json.dumps(matrix_content, indent=2)
                }]
            }
        elif uri == "requirements://resource/ambiguity-log":
            # Return actual ambiguity log from the database
            stored_ambiguities = self.task_storage.get_ambiguities(limit=100)
            
            log_content = {
                "title": "Requirements Ambiguity Log",
                "version": "1.0",
                "generated_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                "ambiguities": [
                    {
                        "id": amb["ambiguity_id"],
                        "requirement_id": amb["requirement_id"],
                        "description": amb["description"],
                        "severity": amb["severity"],
                        "status": amb["status"],
                        "resolution": amb["resolution"],
                        "date_identified": amb.get("date_identified", ""),
                        "date_resolved": amb.get("date_resolved", "")
                    }
                    for amb in stored_ambiguities
                ],
                "summary": {
                    "total_ambiguities": len(stored_ambiguities),
                    "open_ambiguities": len([amb for amb in stored_ambiguities if amb["status"] == "open"]),
                    "resolved_ambiguities": len([amb for amb in stored_ambiguities if amb["status"] == "resolved"]),
                    "in_review_ambiguities": len([amb for amb in stored_ambiguities if amb["status"] == "in_review"])
                },
                "metadata": {
                    "last_updated": time.time(),
                    "generated_by": "Requirement Engineer MCP Server",
                    "status": "active"
                }
            }
            
            return {
                "contents": [{
                    "uri": uri,
                    "text": json.dumps(log_content, indent=2)
                }]
            }
        else:
            # Call parent method for other resources
            return super()._read_resource(resource)

    def _resolve_prompt(self, prompt: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a requirement engineering prompt with given arguments"""
        prompt_name = prompt["name"]

        if prompt_name == "requirements_analysis_prompt":
            stakeholder_inputs = arguments.get("stakeholder_inputs", "")
            business_context = arguments.get("business_context", "")
            
            resolved_text = f"""
# Requirements Analysis Prompt

As a requirements engineer, analyze the following stakeholder inputs and extract structured requirements:

## Stakeholder Inputs:
{stakeholder_inputs}

## Business Context:
{business_context}

Please return a structured document containing:
1. Functional requirements
2. Non-functional requirements
3. Identified ambiguities that need clarification
4. Assumptions made during analysis
5. Dependencies between requirements
"""
            return {
                "contents": [{
                    "type": "text",
                    "text": resolved_text
                }]
            }
        elif prompt_name == "ambiguity_identification_prompt":
            requirements = arguments.get("requirements", "")
            
            resolved_text = f"""
# Ambiguity Identification Prompt

As a requirements engineer, analyze the following requirements for ambiguities and generate clarification questions:

## Requirements:
{requirements}

Please return a document containing:
1. A list of identified ambiguities with details
2. Clarification questions for stakeholders
3. Suggestions for resolving each ambiguity
"""
            return {
                "contents": [{
                    "type": "text",
                    "text": resolved_text
                }]
            }
        elif prompt_name == "business_to_technical_translation_prompt":
            business_requirements = arguments.get("business_requirements", "")
            technical_constraints = arguments.get("technical_constraints", "")
            
            resolved_text = f"""
# Business to Technical Translation Prompt

As a requirements engineer, translate the following business requirements to technical specifications:

## Business Requirements:
{business_requirements}

## Technical Constraints:
{technical_constraints}

Please return a document containing:
1. Technical specifications for each business requirement
2. Implementation considerations
3. Technology recommendations
4. Potential challenges and solutions
"""
            return {
                "contents": [{
                    "type": "text",
                    "text": resolved_text
                }]
            }
        else:
            # Call parent method for other prompts
            return super()._resolve_prompt(prompt, arguments)

    def handle_ping(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle ping request for health check"""
        # Handle case where params is None (when no params are provided in the request)
        if params is None:
            params = {}

        # Perform additional health checks specific to requirement engineering
        health_details = {
            "timestamp": time.time(),
            "status": "healthy",
            "service": "Requirement Engineer MCP Server",
            "checks": {
                "llm_connection": self._check_llm_connection(),
                "database_connection": self._check_database_connection(),
                "task_storage": self._check_task_storage()
            }
        }

        return health_details

    def _check_llm_connection(self) -> str:
        """Check if LLM connection is available"""
        try:
            # Try to make a simple call to the LLM
            import requests
            url = "http://asus-tus:1234/v1/models"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return "ok"
            else:
                return "error"
        except:
            return "unreachable"

    def _check_database_connection(self) -> str:
        """Check if database connection is available"""
        try:
            # Try to query the database
            if hasattr(self, 'task_storage') and self.task_storage:
                # Try to list a few tasks to verify connection
                self.task_storage.list_tasks(limit=1)
                return "ok"
            else:
                return "not_configured"
        except:
            return "error"

    def _check_task_storage(self) -> str:
        """Check if task storage is operational"""
        try:
            if hasattr(self, 'task_storage') and self.task_storage:
                # Try to create and retrieve a test task
                test_task_id = "health_check_" + str(int(time.time()))
                self.task_storage.create_task(test_task_id, "health_check", {}, "testing")
                task = self.task_storage.get_task(test_task_id)
                if task:
                    return "ok"
                else:
                    return "error"
            else:
                return "not_configured"
        except:
            return "error"