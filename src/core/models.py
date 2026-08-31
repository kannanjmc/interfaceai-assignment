"""
Core data models for the computer-use automation system.

This module defines the artifact schema - the structured, typed, versioned
representation of a reusable capability that can be invoked by AI agents.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ActionType(str, Enum):
    """Types of actions the agent can perform."""
    CLICK = "click"
    TYPE = "type"
    NAVIGATE = "navigate"
    WAIT = "wait"
    EXTRACT = "extract"
    SUBMIT = "submit"
    SELECT = "select"


class LocatorType(str, Enum):
    """Strategies for locating UI elements."""
    CSS_SELECTOR = "css_selector"
    XPATH = "xpath"
    TEXT = "text"
    ROLE_AND_TEXT = "role_and_text"
    ARIA_LABEL = "aria_label"
    TEST_ID = "test_id"
    ACCESSIBILITY_ID = "accessibility_id"


class RiskLevel(str, Enum):
    """Risk level of an action."""
    SAFE = "safe"
    REVERSIBLE = "reversible"
    RISKY = "risky"
    IRREVERSIBLE = "irreversible"


class ParameterDefinition(BaseModel):
    """Definition of an input parameter for a capability."""
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (string, number, boolean, etc.)")
    description: str = Field(..., description="Human-readable description")
    required: bool = Field(default=True, description="Whether this parameter is required")
    default_value: Optional[Any] = Field(default=None, description="Default value if not required")
    example: Optional[Any] = Field(default=None, description="Example value for documentation")


class OutputDefinition(BaseModel):
    """Definition of an output/data extraction from a capability."""
    name: str = Field(..., description="Output field name")
    type: str = Field(..., description="Output type")
    description: str = Field(..., description="Human-readable description")
    locator: Dict[str, Any] = Field(..., description="How to locate this data in the UI")


class Locator(BaseModel):
    """How to identify a UI element with fallback strategies."""
    primary: Dict[str, Any] = Field(..., description="Primary locator strategy")
    fallbacks: List[Dict[str, Any]] = Field(default_factory=list, description="Fallback strategies if primary fails")
    locator_type: LocatorType = Field(..., description="Type of locator")
    robustness_notes: Optional[str] = Field(default=None, description="Notes on why this locator is expected to be stable")


class ActionStep(BaseModel):
    """A single step in the automation flow."""
    step_number: int = Field(..., description="Sequential step number")
    action_type: ActionType = Field(..., description="Type of action to perform")
    description: str = Field(..., description="Human-readable description of what this step does")
    
    # Element targeting
    locator: Optional[Locator] = Field(default=None, description="How to find the target element")
    
    # Action-specific data
    value: Optional[str] = Field(default=None, description="Value to type or select")
    url: Optional[str] = Field(default=None, description="URL to navigate to")
    wait_condition: Optional[Dict[str, Any]] = Field(default=None, description="What to wait for")
    
    # Data extraction
    extract_as: Optional[str] = Field(default=None, description="Parameter name to extract result as")
    
    # Risk and safety
    risk_level: RiskLevel = Field(default=RiskLevel.SAFE, description="Risk level of this action")
    requires_confirmation: bool = Field(default=False, description="Whether this action requires human confirmation")
    
    # Error handling
    expected_errors: List[Dict[str, Any]] = Field(default_factory=list, description="Known error states to handle")
    retry_on_failure: bool = Field(default=False, description="Whether to retry this step on failure")
    max_retries: int = Field(default=0, description="Maximum retry attempts")


class Checkpoint(BaseModel):
    """A verification point to confirm the expected state was reached."""
    step_number: int = Field(..., description="Which step this checkpoint verifies")
    condition: Dict[str, Any] = Field(..., description="Condition to verify (e.g., element exists, text visible)")
    description: str = Field(..., description="Human-readable description of what this checkpoint verifies")
    failure_outcome: Optional[str] = Field(default=None, description="Business outcome if checkpoint fails (e.g., 'member_not_found')")


class ErrorHandling(BaseModel):
    """How to handle specific error conditions."""
    error_pattern: str = Field(..., description="Pattern to match error message or condition")
    outcome_type: str = Field(..., description="Type: 'business_outcome', 'recoverable', or 'hard_failure'")
    outcome_value: Optional[str] = Field(default=None, description="Specific outcome value for business outcomes")
    recovery_action: Optional[Dict[str, Any]] = Field(default=None, description="How to recover (for recoverable errors)")


class CapabilityArtifact(BaseModel):
    """
    A structured, reusable capability artifact.
    
    This is the core output of the discovery process - a typed, versioned,
    parameterized automation that can be replayed deterministically without
    LLM involvement.
    """
    # Metadata
    artifact_id: str = Field(..., description="Unique identifier for this artifact")
    version: str = Field(default="1.0.0", description="Semantic version")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    name: str = Field(..., description="Human-readable name for this capability")
    description: str = Field(..., description="Detailed description of what this capability does")
    
    # Target information
    target_app: str = Field(..., description="Application or URL this capability targets")
    target_type: str = Field(..., description="Type: 'web', 'desktop', 'legacy_web', etc.")
    
    # Contract
    input_parameters: List[ParameterDefinition] = Field(default_factory=list, description="Inputs the caller provides")
    outputs: List[OutputDefinition] = Field(default_factory=list, description="Data this capability extracts/returns")
    
    # The flow
    steps: List[ActionStep] = Field(..., description="Ordered steps to execute")
    checkpoints: List[Checkpoint] = Field(default_factory=list, description="Verification points")
    
    # Error handling
    error_handlers: List[ErrorHandling] = Field(default_factory=list, description="Known error conditions and responses")
    
    # Success condition
    success_condition: Dict[str, Any] = Field(..., description="How to verify successful completion")
    
    # Safety and policy
    risk_level: RiskLevel = Field(default=RiskLevel.SAFE, description="Overall risk level of this capability")
    allowlist_tags: List[str] = Field(default_factory=list, description="Policy tags for allowlist matching")
    
    # Discovery metadata
    discovered_by: str = Field(default="llm_agent", description="How this capability was discovered")
    discovery_model: Optional[str] = Field(default=None, description="LLM model used in discovery")
    discovery_timestamp: Optional[datetime] = Field(default=None, description="When discovery was run")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "artifact_id": "lookup_member_balance",
                "version": "1.0.0",
                "name": "Lookup Member Savings Balance",
                "description": "Navigate to member lookup, search by member ID, and extract current savings balance",
                "target_app": "http://localhost:5000",
                "target_type": "web",
                "input_parameters": [
                    {
                        "name": "member_id",
                        "type": "string",
                        "description": "Member ID to look up",
                        "required": True,
                        "example": "12345"
                    }
                ],
                "outputs": [
                    {
                        "name": "balance",
                        "type": "number",
                        "description": "Current savings balance",
                        "locator": {"css_selector": "#balance-display"}
                    }
                ],
                "steps": [],
                "checkpoints": [],
                "error_handlers": [],
                "success_condition": {"element_visible": "#balance-display"}
            }
        }
    )


class ExecutionResult(BaseModel):
    """Result of executing a capability (discovery or replay)."""
    artifact_id: str
    execution_type: str = Field(..., description="'discovery' or 'replay'")
    status: str = Field(..., description="'success', 'business_outcome', or 'failure'")
    
    # Outputs
    outputs: Dict[str, Any] = Field(default_factory=dict, description="Extracted data if successful")
    
    # Error information
    error_type: Optional[str] = Field(default=None, description="Type of error if failed")
    error_message: Optional[str] = Field(default=None, description="Human-readable error message")
    failed_step: Optional[int] = Field(default=None, description="Step number that failed")
    expected: Optional[Any] = Field(default=None, description="What was expected")
    observed: Optional[Any] = Field(default=None, description="What was actually observed")
    
    # Business outcome (distinct from failure)
    business_outcome: Optional[str] = Field(default=None, description="Business outcome if not success/failure")
    
    # Execution metadata
    steps_executed: int = Field(default=0, description="Number of steps completed")
    execution_time_seconds: float = Field(default=0.0, description="Total execution time")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Human handoff
    required_human_handoff: bool = Field(default=False, description="Whether human intervention was required")
    handoff_reason: Optional[str] = Field(default=None, description="Why handoff was needed")
    
    def model_dump_json_safe(self) -> Dict[str, Any]:
        """Convert to dict with datetime serialization for JSON."""
        data = self.model_dump()
        if self.timestamp:
            data['timestamp'] = self.timestamp.isoformat()
        return data


class SessionContext(BaseModel):
    """Context for a live automation session."""
    session_id: str
    target_url: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_step: int = 0
    state: str = Field(default="active", description="active, paused, handed_off, completed, failed")
    controller: str = Field(default="automation", description="automation or human")
    evidence_path: Optional[str] = Field(default=None, description="Path to evidence directory")
    
    def model_dump_json_safe(self) -> Dict[str, Any]:
        """Convert to dict with datetime serialization for JSON."""
        data = self.model_dump()
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        return data
