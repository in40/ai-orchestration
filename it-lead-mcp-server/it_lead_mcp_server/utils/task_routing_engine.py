"""
Task Routing Engine for IT Lead MCP Server
Evaluates tasks against routing rules and determines agent assignment
"""
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from .task_routing_rules import TASK_ROUTING_RULES, AGENT_ENDPOINTS, AGENT_TOOL_MAPPING


@dataclass
class RuleMatchResult:
    """Result of evaluating a rule against a task"""
    matches: bool
    confidence: float
    failure_reason: Optional[str] = None
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None


@dataclass
class RoutingDecision:
    """Final routing decision for a task"""
    success: bool
    assign_to: Optional[str] = None
    tool: Optional[str] = None
    priority: Optional[str] = None
    sequence: Optional[List[str]] = None
    confidence: float = 0.0
    matched_rule_id: Optional[str] = None
    requires_llm_planning: bool = False
    llm_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TaskRoutingEngine:
    """Evaluates tasks against routing rules and determines agent assignment"""
    
    def __init__(self, llm_client=None, service_registry=None):
        self.llm_client = llm_client
        self.service_registry = service_registry
        self.rules = TASK_ROUTING_RULES
        self.agent_endpoints = AGENT_ENDPOINTS.copy()
        self.agent_tool_mapping = AGENT_TOOL_MAPPING.copy()
        
        # Update agent endpoints from registry if available
        if service_registry:
            self._update_agent_endpoints_from_registry()
    
    def _update_agent_endpoints_from_registry(self):
        """Update agent endpoints from the service registry"""
        try:
            services = self.service_registry.list_services()
            for service in services:
                service_name = service.get("name", "").lower()
                endpoint = service.get("endpoint")
                
                if "implementation" in service_name and endpoint:
                    self.agent_endpoints["implementation-engineer"] = endpoint
                elif "requirement" in service_name and endpoint:
                    self.agent_endpoints["requirements-engineer"] = endpoint
                elif "code" in service_name and "review" in service_name and endpoint:
                    self.agent_endpoints["code-reviewer"] = endpoint
                elif "qa" in service_name or "test" in service_name and endpoint:
                    self.agent_endpoints["qa-test-engineer"] = endpoint
                elif "security" in service_name and endpoint:
                    self.agent_endpoints["security-engineer"] = endpoint
                elif "devops" in service_name and endpoint:
                    self.agent_endpoints["devops-engineer"] = endpoint
        except Exception as e:
            print(f"Error updating agent endpoints from registry: {e}")
    
    def evaluate_task(self, task_description: str, assignee: Optional[str] = None,
                     context: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        """
        Evaluate a task against routing rules and return routing decision
        
        Args:
            task_description: The task description text
            assignee: Explicit assignee if provided
            context: Additional context (attachments, metadata, etc.)
        
        Returns:
            RoutingDecision with assignment details or LLM planning flag
        """
        context = context or {}
        
        # Check for explicit assignee first (highest priority)
        if assignee:
            return self._handle_explicit_assignee(assignee, task_description, context)
        
        # Evaluate all rules
        matched_rules = []
        failure_reasons = []
        
        for rule in self.rules:
            match_result = self._evaluate_rule(rule, task_description, context)
            
            if match_result.matches:
                matched_rules.append({
                    "rule": rule,
                    "confidence": match_result.confidence,
                    "rule_id": match_result.rule_id,
                    "rule_name": match_result.rule_name
                })
            else:
                failure_reasons.append({
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "reason": match_result.failure_reason
                })
        
        # Make routing decision
        return self._make_routing_decision(matched_rules, failure_reasons, task_description, context)
    
    def _handle_explicit_assignee(self, assignee: str, task_description: str,
                                  context: Dict[str, Any]) -> RoutingDecision:
        """Handle explicit assignee in task assignment"""
        # Normalize assignee
        assignee_lower = assignee.lower().replace(" ", "-").replace("_", "-")
        
        # Map common variations
        assignee_mapping = {
            "implementation-engineer": "implementation-engineer",
            "implementation-engineer-agent": "implementation-engineer",
            "implementation": "implementation-engineer",
            "requirements-engineer": "requirements-engineer",
            "requirements-engineer-agent": "requirements-engineer",
            "requirements": "requirements-engineer",
            "code-reviewer": "code-reviewer",
            "code-reviewer-agent": "code-reviewer",
            "reviewer": "code-reviewer",
            "qa-test-engineer": "qa-test-engineer",
            "qa-test-engineer-agent": "qa-test-engineer",
            "qa": "qa-test-engineer",
            "tester": "qa-test-engineer",
            "security-engineer": "security-engineer",
            "security-engineer-agent": "security-engineer",
            "security": "security-engineer",
            "devops-engineer": "devops-engineer",
            "devops-engineer-agent": "devops-engineer",
            "devops": "devops-engineer",
        }
        
        normalized_assignee = assignee_mapping.get(assignee_lower, assignee_lower)
        
        # Check if agent is available
        agent_endpoint = self.agent_endpoints.get(normalized_assignee)
        
        # Determine appropriate tool based on task description
        tool = self._determine_tool_for_assignee(normalized_assignee, task_description)
        
        return RoutingDecision(
            success=True,
            assign_to=normalized_assignee,
            tool=tool,
            priority="medium",
            confidence=1.0,
            matched_rule_id="explicit-assignee",
            requires_llm_planning=False,
            metadata={"explicit_assignment": True, "agent_endpoint": agent_endpoint}
        )
    
    def _determine_tool_for_assignee(self, assignee: str, task_description: str) -> str:
        """Determine the appropriate tool for an assignee based on task description"""
        description_lower = task_description.lower()
        
        if assignee == "implementation-engineer":
            if any(kw in description_lower for kw in ["generate", "from spec", "from specification"]):
                return "generate_code_from_spec"
            elif any(kw in description_lower for kw in ["test", "unit test"]):
                return "generate_unit_tests"
            elif any(kw in description_lower for kw in ["refactor", "improve", "optimize"]):
                return "refactor_code"
            else:
                return "implement_feature"
        
        elif assignee == "requirements-engineer":
            if any(kw in description_lower for kw in ["ambiguous", "unclear", "clarify"]):
                return "resolve_ambiguity"
            elif any(kw in description_lower for kw in ["technical", "translate"]):
                return "translate_business_to_technical"
            else:
                return "analyze_requirements"
        
        elif assignee == "code-reviewer":
            return "review_code"
        
        elif assignee == "qa-test-engineer":
            return "generate_test_suite"
        
        elif assignee == "security-engineer":
            return "perform_security_analysis"
        
        elif assignee == "devops-engineer":
            return "orchestrate_deployments"
        
        return "implement_feature"  # Default
    
    def _evaluate_rule(self, rule: Dict[str, Any], task_description: str,
                       context: Dict[str, Any]) -> RuleMatchResult:
        """Evaluate a single rule against a task"""
        conditions = rule.get("conditions", {})
        category = rule.get("category", "keyword")
        
        # Check category-specific conditions
        if category == "keyword":
            return self._evaluate_keyword_rule(conditions, task_description, context, rule)
        elif category == "pattern":
            return self._evaluate_pattern_rule(conditions, task_description, context, rule)
        elif category == "workflow":
            return self._evaluate_workflow_rule(conditions, task_description, context, rule)
        elif category == "explicit":
            return self._evaluate_explicit_rule(conditions, task_description, context, rule)
        
        return RuleMatchResult(matches=False, confidence=0.0, failure_reason="Unknown rule category")
    
    def _evaluate_keyword_rule(self, conditions: Dict[str, Any], task_description: str,
                               context: Dict[str, Any], rule: Dict[str, Any]) -> RuleMatchResult:
        """Evaluate keyword-based rule"""
        description_lower = task_description.lower()
        failures = []
        confidence = 1.0
        
        # Check keywords_any (at least one must match)
        keywords_any = conditions.get("keywords_any", [])
        if keywords_any:
            matched_any = any(kw.lower() in description_lower for kw in keywords_any)
            if not matched_any:
                failures.append(f"No keywords matched from: {keywords_any}")
                confidence -= 0.3
        
        # Check keywords_all (all must match)
        keywords_all = conditions.get("keywords_all", [])
        if keywords_all:
            matched_all = all(kw.lower() in description_lower for kw in keywords_all)
            if not matched_all:
                failures.append(f"Not all required keywords matched: {keywords_all}")
                confidence -= 0.4
        
        # Check keywords_none (none must match)
        keywords_none = conditions.get("keywords_none", [])
        if keywords_none:
            matched_none = not any(kw.lower() in description_lower for kw in keywords_none)
            if not matched_none:
                failures.append(f"Excluded keywords found: {keywords_none}")
                confidence -= 0.5
        
        # Check action_verbs
        action_verbs = conditions.get("action_verbs", [])
        if action_verbs:
            matched_verbs = any(verb.lower() in description_lower for verb in action_verbs)
            if not matched_verbs:
                failures.append(f"No action verbs matched from: {action_verbs}")
                confidence -= 0.2
        
        # Check context-based conditions
        if conditions.get("has_code_diff") and not context.get("code_diff"):
            failures.append("No code diff provided")
            confidence -= 0.4
        
        if conditions.get("document_attached") and not context.get("document"):
            failures.append("No document attached")
            confidence -= 0.4
        
        # Determine match
        matches = confidence >= rule.get("confidence_threshold", 0.7)
        
        return RuleMatchResult(
            matches=matches,
            confidence=max(0.0, confidence),
            failure_reason="; ".join(failures) if failures else None,
            rule_id=rule["id"],
            rule_name=rule["name"]
        )
    
    def _evaluate_pattern_rule(self, conditions: Dict[str, Any], task_description: str,
                               context: Dict[str, Any], rule: Dict[str, Any]) -> RuleMatchResult:
        """Evaluate pattern-based rule"""
        failures = []
        confidence = 1.0
        
        # Check regex pattern
        pattern_regex = conditions.get("pattern_regex")
        if pattern_regex:
            match = re.search(pattern_regex, task_description, re.IGNORECASE)
            if not match:
                failures.append(f"Pattern did not match: {pattern_regex}")
                confidence -= 0.5
        
        # Check acceptance criteria
        if conditions.get("has_acceptance_criteria"):
            has_criteria = any(kw in task_description.lower() for kw in 
                             ["acceptance criteria", "should", "must", "expected"])
            if not has_criteria:
                failures.append("No acceptance criteria found")
                confidence -= 0.3
        
        # Check architectural constraints
        if conditions.get("has_architectural_constraints"):
            has_constraints = any(kw in task_description.lower() for kw in
                                ["architecture", "according to", "following the design"])
            if not has_constraints:
                failures.append("No architectural constraints found")
                confidence -= 0.3
        
        # Check error message
        if conditions.get("has_error_message"):
            has_error = any(kw in task_description for kw in ["Error:", "Exception:", "Traceback"])
            if not has_error:
                failures.append("No error message found")
                confidence -= 0.3
        
        # Check reproduction steps
        if conditions.get("has_reproduction_steps"):
            has_steps = any(kw in task_description.lower() for kw in
                          ["steps:", "to reproduce", "reproduction:", "1)", "2)"])
            if not has_steps:
                failures.append("No reproduction steps found")
                confidence -= 0.3
        
        # Check specifications
        if conditions.get("has_specifications"):
            has_specs = any(kw in task_description.lower() for kw in
                          ["spec", "api spec", "swagger", "openapi", "schema"])
            if not has_specs:
                failures.append("No specifications found")
                confidence -= 0.3
        
        # Check programming language
        if conditions.get("programming_language"):
            has_language = any(kw in task_description.lower() for kw in
                             ["python", "javascript", "java", "go", "typescript", "rust"])
            if not has_language:
                failures.append("No programming language specified")
                confidence -= 0.3
        
        matches = confidence >= rule.get("confidence_threshold", 0.7)
        
        return RuleMatchResult(
            matches=matches,
            confidence=max(0.0, confidence),
            failure_reason="; ".join(failures) if failures else None,
            rule_id=rule["id"],
            rule_name=rule["name"]
        )
    
    def _evaluate_workflow_rule(self, conditions: Dict[str, Any], task_description: str,
                                context: Dict[str, Any], rule: Dict[str, Any]) -> RuleMatchResult:
        """Evaluate workflow/multi-step rule"""
        failures = []
        confidence = 1.0
        
        # Check for workflow keywords
        keywords_any = conditions.get("keywords_any", [])
        if keywords_any:
            matched_any = any(kw.lower() in task_description.lower() for kw in keywords_any)
            if not matched_any:
                failures.append("No workflow keywords found")
                confidence -= 0.3
        
        # Check for multiple phases
        phases = conditions.get("phases", [])
        if phases:
            matched_phases = 0
            for phase in phases:
                phase_keywords = phase.get("keywords", [])
                if any(kw.lower() in task_description.lower() for kw in phase_keyword):
                    matched_phases += 1
            
            if matched_phases < len(phases) * 0.5:
                failures.append(f"Only {matched_phases}/{len(phases)} phases detected")
                confidence -= 0.4
        
        matches = confidence >= rule.get("confidence_threshold", 0.7)
        
        return RuleMatchResult(
            matches=matches,
            confidence=max(0.0, confidence),
            failure_reason="; ".join(failures) if failures else None,
            rule_id=rule["id"],
            rule_name=rule["name"]
        )
    
    def _evaluate_explicit_rule(self, conditions: Dict[str, Any], task_description: str,
                                 context: Dict[str, Any], rule: Dict[str, Any]) -> RuleMatchResult:
        """Evaluate explicit assignee rule"""
        assignee_explicit = conditions.get("assignee_explicit")
        
        if assignee_explicit:
            # This rule is for explicit assignee matching
            # The actual matching happens in _handle_explicit_assignee
            return RuleMatchResult(
                matches=True,
                confidence=1.0,
                rule_id=rule["id"],
                rule_name=rule["name"]
            )
        
        return RuleMatchResult(matches=False, confidence=0.0, failure_reason="No explicit assignee condition")
    
    def _make_routing_decision(self, matched_rules: List[Dict], failure_reasons: List[Dict],
                               task_description: str, context: Dict[str, Any]) -> RoutingDecision:
        """Make final routing decision based on matched rules"""
        
        # No rules matched - trigger LLM planning
        if len(matched_rules) == 0:
            return RoutingDecision(
                success=False,
                requires_llm_planning=True,
                llm_reason="NO_RULES_MATCHED",
                metadata={
                    "failure_reasons": failure_reasons,
                    "task_description": task_description
                }
            )
        
        # Single rule matched
        if len(matched_rules) == 1:
            match = matched_rules[0]
            if match["confidence"] >= 0.8:
                action = match["rule"]["action"]
                return RoutingDecision(
                    success=True,
                    assign_to=action.get("assign_to"),
                    tool=action.get("tool"),
                    priority=action.get("priority", "medium"),
                    confidence=match["confidence"],
                    matched_rule_id=match["rule_id"],
                    requires_llm_planning=False,
                    metadata=action.get("metadata", {})
                )
            else:
                # Low confidence - use LLM to review
                return RoutingDecision(
                    success=False,
                    requires_llm_planning=True,
                    llm_reason="LOW_CONFIDENCE_MATCH",
                    confidence=match["confidence"],
                    metadata={
                        "matched_rule": match["rule_id"],
                        "confidence": match["confidence"],
                        "task_description": task_description
                    }
                )
        
        # Multiple rules matched - check for conflicts
        assignees = set(r["rule"]["action"]["assign_to"] for r in matched_rules)
        
        if len(assignees) > 1:
            # Conflicting assignees - use LLM to resolve
            return RoutingDecision(
                success=False,
                requires_llm_planning=True,
                llm_reason="CONFLICTING_RULES",
                confidence=0.5,
                metadata={
                    "matched_rules": [r["rule_id"] for r in matched_rules],
                    "conflicting_assignees": list(assignees),
                    "task_description": task_description
                }
            )
        else:
            # Same assignee from multiple rules - pick highest confidence
            best_match = max(matched_rules, key=lambda x: x["confidence"])
            action = best_match["rule"]["action"]
            return RoutingDecision(
                success=True,
                assign_to=action.get("assign_to"),
                tool=action.get("tool"),
                priority=action.get("priority", "medium"),
                confidence=best_match["confidence"],
                matched_rule_id=best_match["rule_id"],
                requires_llm_planning=False,
                metadata=action.get("metadata", {})
            )
    
    def get_agent_endpoint(self, agent_id: str) -> Optional[str]:
        """Get the MCP endpoint for an agent"""
        return self.agent_endpoints.get(agent_id)
    
    def get_agent_tool_mapping(self, agent_id: str) -> Dict[str, str]:
        """Get tool mapping for an agent"""
        return self.agent_tool_mapping.get(agent_id, {})
