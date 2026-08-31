"""
Human-in-the-loop escalation and handoff coordination.

This module implements the mechanism to detect when the system is stuck,
route intervention requests to a human operator, transfer control of the
live session, and resume automation after manual intervention.
"""

import asyncio
import json
from typing import Any, Dict, Optional, Callable
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum

from ..core.models import SessionContext, ExecutionResult
from ..core.surface import SurfaceInterface
from ..evidence.collector import EvidenceCollector, StructuredLogger


class HandoffState(str, Enum):
    """States of the handoff process."""
    ACTIVE = "active"  # Automation is running
    PENDING_HANDOFF = "pending_handoff"  # Waiting for human to take control
    IN_HUMAN_CONTROL = "in_human_control"  # Human is operating the session
    RESUMING = "resuming"  # Handing control back to automation
    COMPLETED = "completed"  # Handoff process complete


class InterventionRequest:
    """A request for human intervention."""
    
    def __init__(
        self,
        session_id: str,
        reason: str,
        current_step: int,
        context: Dict[str, Any],
        evidence_path: Optional[str] = None
    ):
        self.session_id = session_id
        self.reason = reason
        self.current_step = current_step
        self.context = context
        self.evidence_path = evidence_path
        self.created_at = datetime.now(timezone.utc)
        self.status = "pending"
        self.resolution: Optional[str] = None
        self.human_actions: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict with datetime serialization for JSON."""
        return {
            "session_id": self.session_id,
            "reason": self.reason,
            "current_step": self.current_step,
            "context": self.context,
            "evidence_path": self.evidence_path,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "resolution": self.resolution,
            "human_actions": self.human_actions
        }


class HandoffCoordinator:
    """
    Coordinates human-in-the-loop handoff operations.
    
    This is the core mechanism for:
    1. Detecting when automation is stuck
    2. Signaling a human operator
    3. Transferring control of the live session
    4. Capturing what the human does
    5. Resuming automation
    """
    
    def __init__(
        self,
        evidence_collector: EvidenceCollector,
        enable_console: bool = True
    ):
        self.evidence = evidence_collector
        self.logger = StructuredLogger(evidence_collector)
        self.enable_console = enable_console
        
        self.current_handoff: Optional[InterventionRequest] = None
        self.handoff_state = HandoffState.ACTIVE
        self.surface: Optional[SurfaceInterface] = None
    
    def set_surface(self, surface: SurfaceInterface) -> None:
        """Set the surface interface for the current session."""
        self.surface = surface
    
    async def request_intervention(
        self,
        session_context: SessionContext,
        reason: str,
        current_step: int,
        context: Dict[str, Any]
    ) -> InterventionRequest:
        """
        Request human intervention.
        
        This is called when automation is stuck or encounters a condition
        it cannot handle safely.
        """
        self.logger.warning(
            current_step,
            f"Requesting human intervention: {reason}",
            context=context
        )
        
        # Create intervention request
        request = InterventionRequest(
            session_id=session_context.session_id,
            reason=reason,
            current_step=current_step,
            context=context,
            evidence_path=session_context.evidence_path
        )
        
        self.current_handoff = request
        self.handoff_state = HandoffState.PENDING_HANDOFF
        
        # Save the request to evidence
        self._save_intervention_request(request)
        
        return request
    
    async def initiate_handoff(self, request: InterventionRequest) -> bool:
        """
        Initiate the handoff - pause automation and prepare for human control.
        
        This is the key seam: automation stops but the session remains live.
        """
        if not self.surface:
            self.logger.error(None, "Cannot initiate handoff: no surface")
            return False
        
        self.logger.info(
            request.current_step,
            "Initiating handoff to human operator"
        )
        
        try:
            # Pause automation on the surface
            await self.surface.pause_automation()
            
            # Update session context
            if self.surface:
                # In a real implementation, this would expose the session
                # to an operator console (e.g., via CDP endpoint)
                pass
            
            self.handoff_state = HandoffState.IN_HUMAN_CONTROL
            request.status = "in_progress"
            
            self._save_intervention_request(request)
            
            # Signal to operator (in this implementation, we use console)
            if self.enable_console:
                await self._signal_operator_console(request)
            
            return True
        
        except Exception as e:
            self.logger.error(
                request.current_step,
                f"Failed to initiate handoff: {str(e)}"
            )
            return False
    
    async def _signal_operator_console(self, request: InterventionRequest) -> None:
        """
        Signal the operator console that intervention is needed.
        
        In a production system, this would:
        - Send a notification to an operator console
        - Expose the live session URL
        - Update a queue/dashboard
        
        For this implementation, we use a simple console-based approach.
        """
        print("\n" + "="*60)
        print("HUMAN INTERVENTION REQUIRED")
        print("="*60)
        print(f"Session ID: {request.session_id}")
        print(f"Reason: {request.reason}")
        print(f"Current Step: {request.current_step}")
        print(f"Context: {json.dumps(request.context, indent=2)}")
        print("="*60)
        print("\nThe automation session is paused and waiting for human control.")
        print("The live session is available for manual operation.")
        print("\nOptions:")
        print("1. Take manual control and complete the task")
        print("2. Resolve the issue and resume automation")
        print("3. Abort the session")
        print("\nPress Enter when you have completed manual operations...")
        print("="*60 + "\n")
    
    async def wait_for_human_completion(self, request: InterventionRequest) -> Dict[str, Any]:
        """
        Wait for the human to complete their manual operations.
        
        In a real implementation, this would wait for a signal from the
        operator console. Here we use console input.
        """
        if self.enable_console:
            # Wait for human to signal completion via console
            input()  # Block until human presses Enter
            
            # Collect information about what the human did
            human_actions = {
                "completed_at": datetime.now().isoformat(),
                "manual_intervention": True,
                "notes": "Human completed manual operations via console"
            }
            
            request.human_actions = human_actions
            request.resolution = "human_completed"
            request.status = "completed"
            
            self._save_intervention_request(request)
            
            return human_actions
        else:
            # Non-interactive mode - simulate human completion
            human_actions = {
                "completed_at": datetime.now().isoformat(),
                "manual_intervention": True,
                "notes": "Simulated human completion (non-interactive mode)"
            }
            
            request.human_actions = human_actions
            request.resolution = "human_completed"
            request.status = "completed"
            
            self._save_intervention_request(request)
            
            return human_actions
    
    async def resume_automation(self, request: InterventionRequest) -> bool:
        """
        Resume automation after human handoff.
        
        The automation continues from the current state of the live session.
        """
        if not self.surface:
            self.logger.error(None, "Cannot resume automation: no surface")
            return False
        
        self.logger.info(
            request.current_step,
            "Resuming automation after human handoff"
        )
        
        try:
            # Resume automation on the surface
            await self.surface.resume_automation()
            
            self.handoff_state = HandoffState.ACTIVE
            self.current_handoff = None
            
            return True
        
        except Exception as e:
            self.logger.error(
                request.current_step,
                f"Failed to resume automation: {str(e)}"
            )
            return False
    
    async def full_handoff_flow(
        self,
        session_context: SessionContext,
        reason: str,
        current_step: int,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the complete handoff flow.
        
        This is a convenience method that orchestrates the entire
        handoff process: request → initiate → wait → resume.
        """
        # Request intervention
        request = await self.request_intervention(
            session_context, reason, current_step, context
        )
        
        # Initiate handoff
        success = await self.initiate_handoff(request)
        if not success:
            return {"success": False, "error": "Failed to initiate handoff"}
        
        # Wait for human completion
        human_actions = await self.wait_for_human_completion(request)
        
        # Resume automation
        success = await self.resume_automation(request)
        if not success:
            return {"success": False, "error": "Failed to resume automation"}
        
        return {
            "success": True,
            "request_id": request.session_id,
            "human_actions": human_actions
        }
    
    def _save_intervention_request(self, request: InterventionRequest) -> None:
        """Save the intervention request to evidence."""
        if not request.evidence_path:
            return
        
        evidence_dir = Path(request.evidence_path)
        evidence_dir.mkdir(parents=True, exist_ok=True)
        
        request_file = evidence_dir / "intervention_request.json"
        
        with open(request_file, 'w') as f:
            json.dump(request.to_dict(), f, indent=2)
    
    def get_handoff_state(self) -> HandoffState:
        """Get the current handoff state."""
        return self.handoff_state
    
    def is_in_human_control(self) -> bool:
        """Check if the session is currently under human control."""
        return self.handoff_state == HandoffState.IN_HUMAN_CONTROL


class EscalationDetector:
    """
    Detects conditions that require human escalation.
    
    This analyzes execution state to determine when automation
    should escalate to a human operator.
    """
    
    def __init__(self, handoff_coordinator: HandoffCoordinator):
        self.coordinator = handoff_coordinator
    
    def should_escalate(
        self,
        step: int,
        error: Optional[str] = None,
        consecutive_failures: int = 0,
        max_consecutive_failures: int = 3
    ) -> tuple[bool, str]:
        """
        Determine if escalation is needed.
        
        Returns:
            (should_escalate, reason) tuple
        """
        # Too many consecutive failures
        if consecutive_failures >= max_consecutive_failures:
            return True, f"Too many consecutive failures ({consecutive_failures})"
        
        # Specific error patterns that require human intervention
        if error:
            error_lower = error.lower()
            if any(pattern in error_lower for pattern in [
                "access denied",
                "permission denied",
                "unauthorized",
                "security"
            ]):
                return True, f"Security/permission error: {error}"
            
            if any(pattern in error_lower for pattern in [
                "stuck",
                "deadlock",
                "hung"
            ]):
                return True, f"System appears stuck: {error}"
        
        return False, ""
    
    async def handle_escalation(
        self,
        session_context: SessionContext,
        reason: str,
        step: int,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle an escalation by triggering the handoff flow."""
        return await self.coordinator.full_handoff_flow(
            session_context, reason, step, context
        )
