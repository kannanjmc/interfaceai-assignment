"""
Tests for core data models.
"""

import pytest
from datetime import datetime
from src.core.models import (
    ActionType, LocatorType, RiskLevel, ParameterDefinition,
    OutputDefinition, Locator, ActionStep, Checkpoint, ErrorHandling,
    CapabilityArtifact, ExecutionResult, SessionContext
)


def test_parameter_definition():
    """Test ParameterDefinition model."""
    param = ParameterDefinition(
        name="member_id",
        type="string",
        description="Member ID to look up",
        required=True,
        example="12345"
    )
    
    assert param.name == "member_id"
    assert param.type == "string"
    assert param.required is True
    assert param.example == "12345"


def test_locator():
    """Test Locator model with fallbacks."""
    locator = Locator(
        locator_type=LocatorType.TEXT,
        primary={"type": "text", "value": "Submit"},
        fallbacks=[
            {"type": "css_selector", "value": "button[type='submit']"},
            {"type": "aria_label", "value": "Submit form"}
        ],
        robustness_notes="Text-based locator is most stable for legacy apps"
    )
    
    assert locator.locator_type == LocatorType.TEXT
    assert len(locator.fallbacks) == 2
    assert locator.robustness_notes is not None


def test_action_step():
    """Test ActionStep model."""
    step = ActionStep(
        step_number=1,
        action_type=ActionType.CLICK,
        description="Click the submit button",
        locator=Locator(
            locator_type=LocatorType.TEXT,
            primary={"type": "text", "value": "Submit"}
        ),
        risk_level=RiskLevel.SAFE
    )
    
    assert step.step_number == 1
    assert step.action_type == ActionType.CLICK
    assert step.risk_level == RiskLevel.SAFE


def test_checkpoint():
    """Test Checkpoint model."""
    checkpoint = Checkpoint(
        step_number=3,
        condition={"type": "url_contains", "value": "/member/12345"},
        description="Verify navigation to member detail page",
        failure_outcome="member_not_found"
    )
    
    assert checkpoint.step_number == 3
    assert checkpoint.failure_outcome == "member_not_found"


def test_error_handling():
    """Test ErrorHandling model."""
    error_handler = ErrorHandling(
        error_pattern="member not found",
        outcome_type="business_outcome",
        outcome_value="not_found",
        recovery_action=None
    )
    
    assert error_handler.outcome_type == "business_outcome"
    assert error_handler.outcome_value == "not_found"


def test_capability_artifact():
    """Test CapabilityArtifact model."""
    artifact = CapabilityArtifact(
        artifact_id="lookup_member_balance",
        name="Lookup Member Balance",
        description="Look up a member and extract their savings balance",
        target_app="http://localhost:5000",
        target_type="legacy_web",
        input_parameters=[
            ParameterDefinition(
                name="member_id",
                type="string",
                description="Member ID",
                required=True
            )
        ],
        outputs=[
            OutputDefinition(
                name="balance",
                type="number",
                description="Savings balance",
                locator={"css_selector": "#balance"}
            )
        ],
        steps=[
            ActionStep(
                step_number=1,
                action_type=ActionType.NAVIGATE,
                description="Navigate to lookup page",
                url="/lookup"
            )
        ],
        success_condition={"type": "element_visible", "value": "#balance"}
    )
    
    assert artifact.artifact_id == "lookup_member_balance"
    assert len(artifact.input_parameters) == 1
    assert len(artifact.outputs) == 1
    assert len(artifact.steps) == 1


def test_execution_result_success():
    """Test ExecutionResult for successful execution."""
    result = ExecutionResult(
        artifact_id="test_artifact",
        execution_type="replay",
        status="success",
        outputs={"balance": 5432.10},
        steps_executed=5,
        execution_time_seconds=2.5
    )
    
    assert result.status == "success"
    assert result.outputs == {"balance": 5432.10}
    assert result.steps_executed == 5


def test_execution_result_business_outcome():
    """Test ExecutionResult for business outcome (not a failure)."""
    result = ExecutionResult(
        artifact_id="test_artifact",
        execution_type="replay",
        status="business_outcome",
        business_outcome="not_found",
        outputs={},
        steps_executed=3,
        execution_time_seconds=1.2
    )
    
    assert result.status == "business_outcome"
    assert result.business_outcome == "not_found"
    # Business outcomes are distinct from failures


def test_execution_result_failure():
    """Test ExecutionResult for failure."""
    result = ExecutionResult(
        artifact_id="test_artifact",
        execution_type="replay",
        status="failure",
        error_type="element_not_found",
        error_message="Could not find submit button",
        failed_step=4,
        expected="Submit button to be present",
        observed="Button not found in DOM",
        steps_executed=3,
        execution_time_seconds=1.8
    )
    
    assert result.status == "failure"
    assert result.error_type == "element_not_found"
    assert result.failed_step == 4
    assert result.expected is not None
    assert result.observed is not None


def test_session_context():
    """Test SessionContext model."""
    context = SessionContext(
        session_id="test_session",
        target_url="http://localhost:5000",
        evidence_path="evidence/test_session"
    )
    
    assert context.session_id == "test_session"
    assert context.state == "active"
    assert context.controller == "automation"


def test_artifact_serialization():
    """Test that artifact can be serialized to JSON."""
    artifact = CapabilityArtifact(
        artifact_id="test_artifact",
        name="Test",
        description="Test artifact",
        target_app="http://localhost:5000",
        target_type="web",
        steps=[],
        success_condition={"type": "step_completed", "step_number": 0}
    )
    
    # Should be able to serialize
    serialized = artifact.model_dump()
    assert isinstance(serialized, dict)
    assert serialized["artifact_id"] == "test_artifact"
    
    # Should be able to deserialize
    deserialized = CapabilityArtifact(**serialized)
    assert deserialized.artifact_id == "test_artifact"
