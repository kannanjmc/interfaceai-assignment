"""
Deterministic replay engine.

This module executes saved capability artifacts deterministically without
LLLM involvement. It handles parameter substitution, checkpoint verification,
and error detection and outcome reporting.

The replay engine is the production execution path - this is how AI agents
would invoke capabilities in a real deployment. Key responsibilities:
- Execute artifacts deterministically without LLM decision-making
- Substitute input parameters into the recorded flow
- Verify checkpoints to ensure expected state is reached
- Handle runtime errors and exceptional states
- Distinguish between business outcomes, recoverable conditions, and hard failures
- Return structured results with clear success/failure information

Performance note: Replay is typically 5-10x faster than discovery
because no LLM reasoning is required.
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path

from ..core.models import (
    CapabilityArtifact, ExecutionResult, SessionContext,
    ActionType, RiskLevel
)
from ..core.surface import SurfaceInterface, SurfaceType, create_surface
from ..safety.guardrails import SafetyGuardrails, AllowlistPolicy, ActionType as SafetyActionType


class ReplayEngine:
    """
    Executes capability artifacts deterministically.
    
    This is the production execution path - an AI agent invokes a capability
    by providing input parameters, and the replay engine executes the recorded
    flow without any LLM decision-making.
    """
    
    def __init__(
        self,
        safety_policy: Optional[AllowlistPolicy] = None
    ):
        self.safety = SafetyGuardrails(safety_policy or self._create_default_policy())
        self.surface: Optional[SurfaceInterface] = None
        self.session_context: Optional[SessionContext] = None
    
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
    
    async def execute(
        self,
        artifact: CapabilityArtifact,
        parameters: Dict[str, Any],
        headless: bool = True,
        evidence_dir: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute a capability artifact with given parameters.
        
        Args:
            artifact: The capability artifact to execute
            parameters: Input parameters for the capability
            headless: Whether to run browser in headless mode
            evidence_dir: Directory to save evidence
        
        Returns:
            ExecutionResult with status, outputs, or error information
        """
        # Initialize session
        session_id = f"replay_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.session_context = SessionContext(
            session_id=session_id,
            target_url=artifact.target_app,
            evidence_path=evidence_dir
        )
        
        # Create evidence directory
        if evidence_dir:
            Path(evidence_dir).mkdir(parents=True, exist_ok=True)
        
        # Connect to surface
        surface_type = SurfaceType(artifact.target_type)
        self.surface = create_surface(surface_type, headless=headless)
        await self.surface.connect(artifact.target_app)
        
        try:
            # Execute the artifact
            result = await self._execute_artifact(artifact, parameters)
            return result
        
        finally:
            # Always disconnect
            if self.surface:
                await self.surface.disconnect()
    
    async def _execute_artifact(
        self,
        artifact: CapabilityArtifact,
        parameters: Dict[str, Any]
    ) -> ExecutionResult:
        """
        Execute all steps in the artifact.
        
        This is the deterministic execution path - no LLM involved.
        """
        start_time = datetime.now(timezone.utc)
        outputs = {}
        
        for step in artifact.steps:
            # Check safety before each step
            if not self._is_step_safe(step):
                return ExecutionResult(
                    artifact_id=artifact.artifact_id,
                    execution_type="replay",
                    status="failure",
                    error_type="safety_violation",
                    error_message=f"Step {step.step_number} blocked by safety policy",
                    failed_step=step.step_number,
                    steps_executed=step.step_number - 1,
                    execution_time_seconds=(datetime.now() - start_time).total_seconds()
                )
            
            # Execute the step
            try:
                step_result = await self._execute_step(step, parameters)
                
                if not step_result.success:
                    # Step failed - check if it's a known error condition
                    error_info = await self._check_error_conditions(artifact, step, step_result)
                    
                    if error_info:
                        # Known error condition
                        if error_info["outcome_type"] == "business_outcome":
                            # Expected business outcome, not a failure
                            return ExecutionResult(
                                artifact_id=artifact.artifact_id,
                                execution_type="replay",
                                status="business_outcome",
                                business_outcome=error_info["outcome_value"],
                                outputs=outputs,
                                failed_step=step.step_number,
                                steps_executed=step.step_number,
                                execution_time_seconds=(datetime.now() - start_time).total_seconds()
                            )
                        elif error_info["outcome_type"] == "recoverable":
                            # Attempt recovery
                            recovery_success = await self._attempt_recovery(error_info["recovery_action"])
                            if not recovery_success:
                                return ExecutionResult(
                                    artifact_id=artifact.artifact_id,
                                    execution_type="replay",
                                    status="failure",
                                    error_type="recovery_failed",
                                    error_message="Failed to recover from error condition",
                                    failed_step=step.step_number,
                                    expected=error_info,
                                    observed={"success": step_result.success, "error": step_result.error},
                                    steps_executed=step.step_number,
                                    execution_time_seconds=(datetime.now() - start_time).total_seconds()
                                )
                            # Recovery succeeded, continue to next step
                            continue
                        else:  # hard_failure
                            return ExecutionResult(
                                artifact_id=artifact.artifact_id,
                                execution_type="replay",
                                status="failure",
                                error_type="error_condition",
                                error_message=f"Error condition: {error_info['error_pattern']}",
                                failed_step=step.step_number,
                                expected=error_info,
                                observed={"success": step_result.success, "error": step_result.error},
                                steps_executed=step.step_number,
                                execution_time_seconds=(datetime.now() - start_time).total_seconds()
                            )
                    else:
                        # Unknown error - hard failure
                        return ExecutionResult(
                            artifact_id=artifact.artifact_id,
                            execution_type="replay",
                            status="failure",
                            error_type="step_execution_failed",
                            error_message=f"Step {step.step_number} failed: {step_result.error}",
                            failed_step=step.step_number,
                            expected=step.description,
                            observed={"success": step_result.success, "error": step_result.error},
                            steps_executed=step.step_number,
                            execution_time_seconds=(datetime.now() - start_time).total_seconds()
                        )
                
                # Collect outputs if this step extracts data
                if step.extract_as and step_result.extracted_value:
                    outputs[step.extract_as] = step_result.extracted_value
                
                # Verify checkpoint if this step has one
                checkpoint = self._find_checkpoint(artifact, step.step_number)
                if checkpoint:
                    checkpoint_passed = await self._verify_checkpoint(checkpoint)
                    if not checkpoint_passed:
                        # Checkpoint failed - check if it has a business outcome
                        if checkpoint.failure_outcome:
                            return ExecutionResult(
                                artifact_id=artifact.artifact_id,
                                execution_type="replay",
                                status="business_outcome",
                                business_outcome=checkpoint.failure_outcome,
                                outputs=outputs,
                                failed_step=step.step_number,
                                steps_executed=step.step_number,
                                execution_time_seconds=(datetime.now() - start_time).total_seconds()
                            )
                        else:
                            return ExecutionResult(
                                artifact_id=artifact.artifact_id,
                                execution_type="replay",
                                status="failure",
                                error_type="checkpoint_failed",
                                error_message=f"Checkpoint failed at step {step.step_number}",
                                failed_step=step.step_number,
                                expected=checkpoint.condition,
                                observed="condition not met",
                                steps_executed=step.step_number,
                                execution_time_seconds=(datetime.now() - start_time).total_seconds()
                            )
                
                # Take evidence screenshot
                if self.session_context.evidence_path:
                    screenshot_path = f"{self.session_context.evidence_path}/step_{step.step_number}.png"
                    await self.surface.take_screenshot(screenshot_path)
            
            except Exception as e:
                return ExecutionResult(
                    artifact_id=artifact.artifact_id,
                    execution_type="replay",
                    status="failure",
                    error_type="exception",
                    error_message=str(e),
                    failed_step=step.step_number,
                    steps_executed=step.step_number - 1,
                    execution_time_seconds=(datetime.now() - start_time).total_seconds()
                )
        
        # All steps completed successfully
        # Verify final success condition
        success_verified = await self._verify_success_condition(artifact.success_condition)
        
        if not success_verified:
            return ExecutionResult(
                artifact_id=artifact.artifact_id,
                execution_type="replay",
                status="failure",
                error_type="success_condition_failed",
                error_message="Final success condition not met",
                failed_step=len(artifact.steps),
                expected=artifact.success_condition,
                observed="condition not met",
                steps_executed=len(artifact.steps),
                execution_time_seconds=(datetime.now() - start_time).total_seconds()
            )
        
        return ExecutionResult(
            artifact_id=artifact.artifact_id,
            execution_type="replay",
            status="success",
            outputs=outputs,
            steps_executed=len(artifact.steps),
            execution_time_seconds=(datetime.now() - start_time).total_seconds()
        )
    
    def _is_step_safe(self, step) -> bool:
        """Check if a step is allowed by safety policy."""
        try:
            safety_action = SafetyActionType(step.action_type.value)
            allowed, reason = self.safety.is_action_allowed(safety_action)
            return allowed
        except ValueError:
            return False
    
    async def _execute_step(self, step, parameters: Dict[str, Any]) -> "StepResult":
        """Execute a single step with parameter substitution."""
        # Substitute parameters in values
        value = self._substitute_parameters(step.value, parameters)
        url = self._substitute_parameters(step.url, parameters)
        
        # Handle retries
        max_attempts = 1 + (step.max_retries if step.retry_on_failure else 0)
        
        for attempt in range(max_attempts):
            try:
                # Execute the action
                success = await self._execute_action(step, value, url)
                
                if success:
                    # If this is an extraction step, extract the value
                    extracted_value = None
                    if step.extract_as and step.locator:
                        extracted_value = await self.surface.extract_text(step.locator.dict())
                    
                    return StepResult(success=True, extracted_value=extracted_value)
                else:
                    if attempt < max_attempts - 1:
                        # Wait before retry
                        await asyncio.sleep(1)
                    else:
                        return StepResult(success=False, error="Action failed after retries")
            
            except Exception as e:
                if attempt < max_attempts - 1:
                    await asyncio.sleep(1)
                else:
                    return StepResult(success=False, error=str(e))
        
        return StepResult(success=False, error="Max retries exceeded")
    
    def _substitute_parameters(self, value: Optional[str], parameters: Dict[str, Any]) -> Optional[str]:
        """Substitute parameter placeholders with actual values."""
        if value is None:
            return None
        
        # Handle {{parameter}} syntax
        if "{{" in value and "}}" in value:
            for param_name, param_value in parameters.items():
                placeholder = f"{{{{{param_name}}}}}"
                value = value.replace(placeholder, str(param_value))
        
        return value
    
    async def _execute_action(self, step, value: Optional[str], url: Optional[str]) -> bool:
        """Execute a single action."""
        locator = step.locator.dict() if step.locator else None
        
        if step.action_type == ActionType.CLICK:
            return await self.surface.click(locator)
        elif step.action_type == ActionType.TYPE:
            return await self.surface.type_text(locator, value or "")
        elif step.action_type == ActionType.NAVIGATE:
            return await self.surface.navigate(url or "")
        elif step.action_type == ActionType.WAIT:
            condition = step.wait_condition or {}
            return await self.surface.wait_for(condition)
        elif step.action_type == ActionType.EXTRACT:
            # Extraction is handled separately
            return True
        elif step.action_type == ActionType.SELECT:
            # Select is typically a click on an option
            return await self.surface.click(locator)
        elif step.action_type == ActionType.SUBMIT:
            return await self.surface.click(locator)
        else:
            return False
    
    def _find_checkpoint(self, artifact: CapabilityArtifact, step_number: int):
        """Find checkpoint for a given step."""
        for checkpoint in artifact.checkpoints:
            if checkpoint.step_number == step_number:
                return checkpoint
        return None
    
    async def _verify_checkpoint(self, checkpoint) -> bool:
        """Verify that a checkpoint condition is met."""
        condition = checkpoint.condition
        condition_type = condition.get("type")
        value = condition.get("value")
        
        try:
            if condition_type == "url_contains":
                state = await self.surface.get_state()
                return value in state.url if state.url else False
            elif condition_type == "element_visible":
                element = await self.surface.find_element({"type": "css_selector", "value": value})
                return element is not None and element.visible
            elif condition_type == "text_present":
                state = await self.surface.get_state()
                # Check in accessibility tree or page text
                if state.accessibility_tree:
                    return self._text_in_tree(state.accessibility_tree, value)
                return False
            else:
                return False
        except Exception:
            return False
    
    def _text_in_tree(self, tree: Dict[str, Any], text: str) -> bool:
        """Recursively search for text in accessibility tree."""
        if "name" in tree and text.lower() in tree["name"].lower():
            return True
        if "value" in tree and text.lower() in str(tree["value"]).lower():
            return True
        if "children" in tree:
            for child in tree["children"]:
                if self._text_in_tree(child, text):
                    return True
        return False
    
    async def _check_error_conditions(self, artifact: CapabilityArtifact, step, step_result: "StepResult") -> Optional[Dict[str, Any]]:
        """Check if the step failure matches a known error condition."""
        state = await self.surface.get_state()
        
        for handler in artifact.error_handlers:
            pattern = handler.error_pattern.lower()
            
            # Check if pattern appears in current state
            state_text = self._state_to_text(state)
            if pattern in state_text.lower():
                return {
                    "error_pattern": handler.error_pattern,
                    "outcome_type": handler.outcome_type,
                    "outcome_value": handler.outcome_value,
                    "recovery_action": handler.recovery_action.dict() if handler.recovery_action else None
                }
        
        return None
    
    def _state_to_text(self, state) -> str:
        """Convert state to searchable text."""
        parts = []
        if state.url:
            parts.append(state.url)
        if state.title:
            parts.append(state.title)
        if state.accessibility_tree:
            parts.append(str(state.accessibility_tree))
        return " ".join(parts)
    
    async def _attempt_recovery(self, recovery_action: Dict[str, Any]) -> bool:
        """Attempt a recovery action."""
        action_type = recovery_action.get("action")
        
        try:
            if action_type == "navigate":
                url = recovery_action.get("url")
                return await self.surface.navigate(url)
            elif action_type == "click":
                locator = recovery_action.get("locator")
                return await self.surface.click(locator)
            # Add other recovery actions as needed
            return False
        except Exception:
            return False
    
    async def _verify_success_condition(self, condition: Dict[str, Any]) -> bool:
        """Verify the final success condition."""
        condition_type = condition.get("type")
        
        if condition_type == "step_completed":
            # Already verified by completing all steps
            return True
        elif condition_type == "element_visible":
            value = condition.get("value")
            element = await self.surface.find_element({"type": "css_selector", "value": value})
            return element is not None and element.visible
        elif condition_type == "url_contains":
            value = condition.get("value")
            state = await self.surface.get_state()
            return value in state.url if state.url else False
        
        return False


class StepResult:
    """Result of executing a single step."""
    def __init__(self, success: bool, error: Optional[str] = None, extracted_value: Optional[str] = None):
        self.success = success
        self.error = error
        self.extracted_value = extracted_value
