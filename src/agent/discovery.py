"""
LLM-driven discovery agent.

This module implements the observe → decide → act loop that uses an LLM
to figure out how to accomplish a goal by driving a real application surface.

The discovery agent is responsible for:
- Observing the current application state
- Deciding what action to take next based on the goal
- Executing actions and handling their results
- Recording successful runs as structured capability artifacts
- Detecting when human intervention is needed

This is the only component that uses the LLM. Production execution
(replay) is deterministic and does not involve the LLM.
"""

import json
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path

from openai import AsyncOpenAI

from ..core.models import (
    ActionType, LocatorType, RiskLevel, ActionStep, Checkpoint,
    ErrorHandling, CapabilityArtifact, ExecutionResult, SessionContext
)
from ..core.surface import SurfaceInterface, SurfaceType, create_surface
from ..safety.guardrails import SafetyGuardrails, AllowlistPolicy, ActionType as SafetyActionType


class DiscoveryAgent:
    """
    LLM-driven agent that discovers how to accomplish a goal.
    
    The agent observes the current application state, decides what action to take,
    executes it, and repeats until the goal is met or a stopping condition is hit.
    """
    
    def __init__(
        self,
        llm_provider: str = "anthropic",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        safety_policy: Optional[AllowlistPolicy] = None
    ):
        self.llm_provider = llm_provider
        self.model = model or (self._get_default_model(llm_provider))
        self.api_key = api_key
        
        # Initialize LLM client
        if llm_provider == "openai":
            self.client = AsyncOpenAI(api_key=api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}. Currently only 'openai' is supported.")
        
        # Safety guardrails
        self.safety = SafetyGuardrails(safety_policy or self._create_default_policy())
        
        # State tracking
        self.surface: Optional[SurfaceInterface] = None
        self.session_context: Optional[SessionContext] = None
        self.trace: List[Dict[str, Any]] = []
        self.steps: List[ActionStep] = []
        self.current_step = 0
    
    def _get_default_model(self, provider: str) -> str:
        """Get default model for provider."""
        if provider == "openai":
            return "gpt-4o"
        else:
            raise ValueError(f"Unknown provider: {provider}. Currently only 'openai' is supported.")
    
    def _create_default_policy(self) -> AllowlistPolicy:
        """Create default safety policy."""
        return AllowlistPolicy(
            allowed_domains={"localhost", "127.0.0.1"},
            allowed_actions={
                SafetyActionType.CLICK,
                SafetyActionType.TYPE,
                SafetyActionType.NAVIGATE,
                SafetyActionType.WAIT,
                SafetyActionType.EXTRACT,
                SafetyActionType.SELECT,
            },
            risky_actions={
                SafetyActionType.SUBMIT,
                SafetyActionType.DELETE,
                SafetyActionType.CONFIRM,
            },
            max_steps=50,
            timeout_seconds=300
        )
    
    async def discover(
        self,
        goal: str,
        target_url: str,
        surface_type: SurfaceType = SurfaceType.LEGACY_WEB,
        headless: bool = True,
        evidence_dir: Optional[str] = None
    ) -> Tuple[CapabilityArtifact, ExecutionResult]:
        """
        Run discovery to learn how to accomplish the goal.
        
        Args:
            goal: Natural language description of what to accomplish
            target_url: URL of the target application
            surface_type: Type of surface (web, legacy_web, desktop)
            headless: Whether to run browser in headless mode
            evidence_dir: Directory to save evidence (screenshots, logs)
        
        Returns:
            Tuple of (artifact, execution_result)
        """
        # Initialize session
        session_id = f"discovery_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.session_context = SessionContext(
            session_id=session_id,
            target_url=target_url,
            evidence_path=evidence_dir
        )
        
        # Create evidence directory
        if evidence_dir:
            Path(evidence_dir).mkdir(parents=True, exist_ok=True)
        
        # Connect to surface
        self.surface = create_surface(surface_type, headless=headless)
        await self.surface.connect(target_url)
        
        try:
            # Run the discovery loop
            result = await self._run_discovery_loop(goal)
            
            # Generate artifact from discovered steps
            artifact = self._generate_artifact(goal, target_url, surface_type)
            
            return artifact, result
        
        finally:
            # Always disconnect
            if self.surface:
                await self.surface.disconnect()
    
    async def _run_discovery_loop(self, goal: str) -> ExecutionResult:
        """
        Main discovery loop: observe → decide → act.
        
        Returns:
            ExecutionResult with status and any outputs
        """
        max_steps = self.safety.policy.max_steps
        start_time = datetime.now()
        
        for step_num in range(1, max_steps + 1):
            self.current_step = step_num
            
            # Observe current state
            state = await self.surface.get_state()
            
            # Decide what action to take
            action_decision = await self._decide_action(goal, state, step_num)
            
            if action_decision.get("done"):
                # Goal achieved
                return ExecutionResult(
                    artifact_id=self.session_context.session_id,
                    execution_type="discovery",
                    status="success",
                    outputs=action_decision.get("outputs", {}),
                    steps_executed=step_num - 1,
                    execution_time_seconds=(datetime.now() - start_time).total_seconds()
                )
            
            if action_decision.get("stuck"):
                # Agent is stuck, need human intervention
                return await self._handle_stuck_state(action_decision, step_num, start_time)
            
            # Check safety before executing
            action_type = action_decision.get("action_type")
            if not self._is_action_safe(action_type, action_decision):
                return ExecutionResult(
                    artifact_id=self.session_context.session_id,
                    execution_type="discovery",
                    status="failure",
                    error_type="safety_violation",
                    error_message=f"Action '{action_type}' blocked by safety policy",
                    failed_step=step_num,
                    steps_executed=step_num - 1,
                    execution_time_seconds=(datetime.now() - start_time).total_seconds()
                )
            
            # Execute the action
            success = await self._execute_action(action_decision, step_num)
            
            if not success:
                return ExecutionResult(
                    artifact_id=self.session_context.session_id,
                    execution_type="discovery",
                    status="failure",
                    error_type="action_failed",
                    error_message=f"Failed to execute action: {action_decision.get('description')}",
                    failed_step=step_num,
                    steps_executed=step_num - 1,
                    execution_time_seconds=(datetime.now() - start_time).total_seconds()
                )
            
            # Record the step for artifact generation
            self._record_step(action_decision, step_num)
            
            # Take evidence screenshot
            if self.session_context.evidence_path:
                screenshot_path = f"{self.session_context.evidence_path}/step_{step_num}.png"
                await self.surface.take_screenshot(screenshot_path)
        
        # Max steps reached without completion
        return ExecutionResult(
            artifact_id=self.session_context.session_id,
            execution_type="discovery",
            status="failure",
            error_type="max_steps_exceeded",
            error_message=f"Did not complete goal within {max_steps} steps",
            failed_step=max_steps,
            steps_executed=max_steps,
            execution_time_seconds=(datetime.now() - start_time).total_seconds()
        )
    
    async def _decide_action(self, goal: str, state, step_num: int) -> Dict[str, Any]:
        """
        Use LLM to decide what action to take next.
        
        This is the core intelligence - the LLM observes the current state
        and decides what action will progress toward the goal.
        """
        # Prepare the prompt with current state
        state_description = self._format_state_for_llm(state)
        
        # Build conversation history
        messages = [
            {
                "role": "user",
                "content": f"""You are a computer-use automation agent. Your goal is: {goal}

Current application state:
{state_description}

Step {step_num} of discovery. You have already completed {step_num - 1} steps.

Analyze the current state and decide what action to take next. Respond with a JSON object in this format:
{{
    "action_type": "click|type|navigate|wait|extract|submit|select",
    "description": "Human-readable description of what you're doing and why",
    "locator": {{
        "type": "css_selector|xpath|text|role_and_text|aria_label",
        "value": "the locator value",
        "fallbacks": [{{"type": "...", "value": "..."}}]
    }},
    "value": "text to type (if action_type is 'type' or 'select')",
    "url": "URL to navigate to (if action_type is 'navigate')",
    "wait_condition": {{"type": "element_visible", "value": "selector"}} (optional),
    "extract_as": "parameter_name" (if extracting data),
    "done": false (set to true if goal is achieved),
    "stuck": false (set to true if you cannot proceed and need human help),
    "outputs": {{}} (if done, any extracted outputs)
}}

Prioritize robust locators that will work on legacy applications:
- Prefer text-based locators over CSS selectors
- Use role_and_text for accessibility-based targeting
- Include fallbacks for fragile selectors
- Avoid dynamic IDs

If you have achieved the goal, set "done": true and include any outputs.
If you are stuck and cannot proceed, set "stuck": true and explain why."""
            }
        ]
        
        # Call LLM (OpenAI)
        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=2048,
            messages=messages
        )
        content = response.choices[0].message.content
        
        # Parse JSON response
        try:
            # Extract JSON from response (handle potential markdown formatting)
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            json_str = content[json_start:json_end]
            decision = json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback if LLM doesn't return valid JSON
            decision = {
                "stuck": True,
                "description": f"Failed to parse LLM response as JSON: {str(e)}"
            }
        
        # Log the decision
        self.trace.append({
            "step": step_num,
            "state": state_description,
            "decision": decision,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return decision
    
    def _format_state_for_llm(self, state) -> str:
        """Format the current state for LLM consumption."""
        parts = []
        
        if state.url:
            parts.append(f"URL: {state.url}")
        
        if state.title:
            parts.append(f"Page Title: {state.title}")
        
        if state.accessibility_tree:
            # Format accessibility tree as readable text
            parts.append(f"Accessibility Tree:\n{json.dumps(state.accessibility_tree, indent=2)}")
        
        return "\n".join(parts)
    
    def _is_action_safe(self, action_type: str, decision: Dict[str, Any]) -> bool:
        """Check if action is allowed by safety policy."""
        try:
            safety_action = SafetyActionType(action_type)
            allowed, reason = self.safety.is_action_allowed(safety_action)
            return allowed
        except ValueError:
            return False
    
    async def _execute_action(self, decision: Dict[str, Any], step_num: int) -> bool:
        """Execute the decided action."""
        action_type = decision.get("action_type")
        locator = decision.get("locator")
        
        try:
            if action_type == "click":
                return await self.surface.click(locator)
            elif action_type == "type":
                value = decision.get("value", "")
                return await self.surface.type_text(locator, value)
            elif action_type == "navigate":
                url = decision.get("url")
                return await self.surface.navigate(url)
            elif action_type == "wait":
                condition = decision.get("wait_condition", {})
                return await self.surface.wait_for(condition)
            elif action_type == "extract":
                text = await self.surface.extract_text(locator)
                if text and decision.get("extract_as"):
                    # Store for later output
                    decision["_extracted_value"] = text
                return text is not None
            elif action_type == "select":
                value = decision.get("value", "")
                # For select, we need to click the option
                return await self.surface.click(locator)
            elif action_type == "submit":
                # Submit is typically a click on a submit button
                return await self.surface.click(locator)
            else:
                return False
        except Exception as e:
            print(f"Error executing action: {e}")
            return False
    
    def _record_step(self, decision: Dict[str, Any], step_num: int) -> None:
        """Record a step for artifact generation."""
        action_type_str = decision.get("action_type", "click")
        try:
            action_type = ActionType(action_type_str)
        except ValueError:
            action_type = ActionType.CLICK
        
        # Map action type to risk level
        risk_level = RiskLevel.SAFE
        if action_type in [ActionType.SUBMIT, ActionType.DELETE]:
            risk_level = RiskLevel.RISKY
        
        step = ActionStep(
            step_number=step_num,
            action_type=action_type,
            description=decision.get("description", ""),
            locator=decision.get("locator"),
            value=decision.get("value"),
            url=decision.get("url"),
            wait_condition=decision.get("wait_condition"),
            extract_as=decision.get("extract_as"),
            risk_level=risk_level
        )
        
        self.steps.append(step)
    
    async def _handle_stuck_state(self, decision: Dict[str, Any], step_num: int, start_time: datetime) -> ExecutionResult:
        """Handle when the agent is stuck and needs human intervention."""
        # In a full implementation, this would trigger the handoff mechanism
        return ExecutionResult(
            artifact_id=self.session_context.session_id,
            execution_type="discovery",
            status="failure",
            error_type="agent_stuck",
            error_message=decision.get("description", "Agent is stuck"),
            failed_step=step_num,
            required_human_handoff=True,
            handoff_reason="Agent could not determine next action",
            steps_executed=step_num - 1,
            execution_time_seconds=(datetime.now() - start_time).total_seconds()
        )
    
    def _generate_artifact(self, goal: str, target_url: str, surface_type: SurfaceType) -> CapabilityArtifact:
        """Generate a capability artifact from the discovered steps."""
        # Infer input parameters from the steps
        input_params = self._infer_input_parameters()
        
        # Infer outputs from extraction steps
        outputs = self._infer_outputs()
        
        # Generate checkpoints at key steps
        checkpoints = self._generate_checkpoints()
        
        # Generate error handlers for common conditions
        error_handlers = self._generate_error_handlers()
        
        # Success condition (typically the last step)
        success_condition = {
            "type": "step_completed",
            "step_number": len(self.steps)
        }
        
        artifact = CapabilityArtifact(
            artifact_id=f"capability_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            name=self._generate_name(goal),
            description=goal,
            target_app=target_url,
            target_type=surface_type.value,
            input_parameters=input_params,
            outputs=outputs,
            steps=self.steps,
            checkpoints=checkpoints,
            error_handlers=error_handlers,
            success_condition=success_condition,
            discovery_model=self.model,
            discovery_timestamp=datetime.now(timezone.utc)
        )
        
        return artifact
    
    def _generate_name(self, goal: str) -> str:
        """Generate a concise name from the goal."""
        # Simple heuristic: take first few words
        words = goal.split()[:5]
        return " ".join(words).title()
    
    def _infer_input_parameters(self) -> List:
        """Infer input parameters from the discovered steps."""
        # Look for steps that use placeholder values
        params = []
        
        for step in self.steps:
            if step.value and "{{" in step.value:
                # This looks like a parameter
                param_name = step.value.strip("{}").strip()
                params.append({
                    "name": param_name,
                    "type": "string",
                    "description": f"Value for {param_name}",
                    "required": True
                })
        
        return params
    
    def _infer_outputs(self) -> List:
        """Infer outputs from extraction steps."""
        outputs = []
        
        for step in self.steps:
            if step.extract_as:
                outputs.append({
                    "name": step.extract_as,
                    "type": "string",
                    "description": f"Extracted from step {step.step_number}",
                    "locator": step.locator.dict() if step.locator else {}
                })
        
        return outputs
    
    def _generate_checkpoints(self) -> List[Checkpoint]:
        """Generate checkpoints at key verification points."""
        checkpoints = []
        
        # Add checkpoint after navigation
        for step in self.steps:
            if step.action_type == ActionType.NAVIGATE:
                checkpoints.append(Checkpoint(
                    step_number=step.step_number,
                    condition={"type": "url_contains", "value": step.url},
                    description=f"Verified navigation to {step.url}"
                ))
        
        return checkpoints
    
    def _generate_error_handlers(self) -> List[ErrorHandling]:
        """Generate error handlers for common conditions."""
        # Start with some common error patterns
        handlers = [
            ErrorHandling(
                error_pattern="member not found|record not found",
                outcome_type="business_outcome",
                outcome_value="not_found",
                recovery_action=None
            ),
            ErrorHandling(
                error_pattern="session expired|timeout",
                outcome_type="recoverable",
                recovery_action={"action": "navigate", "url": "/"}
            )
        ]
        
        return handlers
