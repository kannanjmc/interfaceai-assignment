"""
Tests for safety guardrails and sensitive data redaction.
"""

import pytest
from src.safety.guardrails import (
    SafetyGuardrails, AllowlistPolicy, SensitiveDataRedactor,
    SensitiveDataPattern, RiskLevel, ActionType as SafetyActionType
)


def test_allowlist_policy():
    """Test AllowlistPolicy model."""
    policy = AllowlistPolicy(
        allowed_domains={"localhost", "127.0.0.1"},
        allowed_actions={SafetyActionType.CLICK, SafetyActionType.TYPE},
        risky_actions={SafetyActionType.SUBMIT, SafetyActionType.DELETE},
        max_steps=50
    )
    
    assert "localhost" in policy.allowed_domains
    assert SafetyActionType.CLICK in policy.allowed_actions
    assert SafetyActionType.SUBMIT in policy.risky_actions


def test_safety_guardrails_allowed_action():
    """Test that allowed actions pass safety check."""
    policy = AllowlistPolicy(
        allowed_domains={"localhost"},
        allowed_actions={SafetyActionType.CLICK, SafetyActionType.TYPE}
    )
    guardrails = SafetyGuardrails(policy)
    
    allowed, reason = guardrails.is_action_allowed(SafetyActionType.CLICK, "http://localhost/page")
    assert allowed is True
    assert reason is None


def test_safety_guardrails_blocked_action():
    """Test that blocked actions fail safety check."""
    policy = AllowlistPolicy(
        allowed_domains={"localhost"},
        allowed_actions={SafetyActionType.CLICK},
        blocked_actions={SafetyActionType.DELETE}
    )
    guardrails = SafetyGuardrails(policy)
    
    allowed, reason = guardrails.is_action_allowed(SafetyActionType.DELETE)
    assert allowed is False
    assert "blocked" in reason.lower()


def test_safety_guardrails_domain_check():
    """Test domain allowlist enforcement."""
    policy = AllowlistPolicy(
        allowed_domains={"localhost"},
        allowed_actions={SafetyActionType.NAVIGATE}
    )
    guardrails = SafetyGuardrails(policy)
    
    # Allowed domain
    allowed, _ = guardrails.is_action_allowed(SafetyActionType.NAVIGATE, "http://localhost/page")
    assert allowed is True
    
    # Disallowed domain
    allowed, reason = guardrails.is_action_allowed(SafetyActionType.NAVIGATE, "http://evil.com/page")
    assert allowed is False
    assert "domain" in reason.lower()


def test_risk_assessment():
    """Test risk level assessment."""
    policy = AllowlistPolicy(
        allowed_actions={SafetyActionType.CLICK, SafetyActionType.TYPE, SafetyActionType.SUBMIT},
        risky_actions={SafetyActionType.SUBMIT}
    )
    guardrails = SafetyGuardrails(policy)
    
    # Safe action
    risk = guardrails.assess_action_risk(SafetyActionType.CLICK)
    assert risk == RiskLevel.SAFE
    
    # Risky action
    risk = guardrails.assess_action_risk(SafetyActionType.SUBMIT)
    assert risk == RiskLevel.RISKY


def test_sensitive_data_redactor_ssn():
    """Test SSN redaction."""
    text = "Member SSN: 123-45-6789"
    redacted = SensitiveDataRedactor.redact_text(text)
    assert "123-45-6789" not in redacted
    assert "[SSN_REDACTED]" in redacted


def test_sensitive_data_redactor_credit_card():
    """Test credit card redaction."""
    text = "Card number: 4111-1111-1111-1111"
    redacted = SensitiveDataRedactor.redact_text(text)
    assert "4111-1111-1111-1111" not in redacted
    assert "[CC_REDACTED]" in redacted


def test_sensitive_data_redactor_api_key():
    """Test API key redaction."""
    text = "api_key: sk-1234567890abcdef"
    redacted = SensitiveDataRedactor.redact_text(text)
    assert "sk-1234567890abcdef" not in redacted
    assert "[API_KEY_REDACTED]" in redacted


def test_sensitive_data_redactor_password():
    """Test password redaction."""
    text = "password: secret123"
    redacted = SensitiveDataRedactor.redact_text(text)
    assert "secret123" not in redacted
    assert "[PASSWORD_REDACTED]" in redacted


def test_sensitive_data_redactor_email():
    """Test email redaction."""
    text = "Contact: user@example.com"
    redacted = SensitiveDataRedactor.redact_text(text)
    assert "user@example.com" not in redacted
    assert "[EMAIL_REDACTED]" in redacted


def test_sensitive_data_redactor_dict():
    """Test redaction from dictionary."""
    data = {
        "name": "John Doe",
        "ssn": "123-45-6789",
        "email": "john@example.com",
        "balance": 1000
    }
    
    redacted = SensitiveDataRedactor.redact_dict(data)
    
    assert redacted["name"] == "John Doe"  # Not sensitive
    assert redacted["ssn"] == "[SSN_REDACTED]"
    assert redacted["email"] == "[EMAIL_REDACTED]"
    assert redacted["balance"] == 1000  # Not sensitive


def test_sensitive_data_redactor_nested_dict():
    """Test redaction from nested dictionary."""
    data = {
        "member": {
            "name": "Jane Doe",
            "contact": {
                "email": "jane@example.com",
                "phone": "555-1234"
            }
        },
        "account": {
            "number": "1234567890",
            "balance": 5000
        }
    }
    
    redacted = SensitiveDataRedactor.redact_dict(data)
    
    assert redacted["member"]["name"] == "Jane Doe"
    assert redacted["member"]["contact"]["email"] == "[EMAIL_REDACTED]"
    assert "[ACCOUNT_REDACTED]" in str(redacted["account"]["number"])


def test_sensitive_data_redactor_sensitive_keys():
    """Test redaction based on key names."""
    data = {
        "username": "john_doe",
        "password": "secret123",
        "token": "abc123xyz",
        "normal_field": "some value"
    }
    
    redacted = SensitiveDataRedactor.redact_dict(data)
    
    assert redacted["username"] == "john_doe"
    assert redacted["password"] == "[PASSWORD_REDACTED]"
    assert redacted["token"] == "[TOKEN_REDACTED]"
    assert redacted["normal_field"] == "some value"


def test_custom_sensitive_pattern():
    """Test adding custom sensitive data pattern."""
    custom_pattern = SensitiveDataPattern(
        name="custom_id",
        pattern=r"CUST-\d{6}",
        description="Customer ID",
        redaction_placeholder="[CUST_ID_REDACTED]"
    )
    
    SensitiveDataRedactor.add_custom_pattern(custom_pattern)
    
    text = "Customer ID: CUST-123456"
    redacted = SensitiveDataRedactor.redact_text(text)
    
    assert "CUST-123456" not in redacted
    assert "[CUST_ID_REDACTED]" in redacted


def test_should_require_confirmation():
    """Test confirmation requirement for risky actions."""
    policy = AllowlistPolicy(
        allowed_actions={SafetyActionType.CLICK, SafetyActionType.SUBMIT, SafetyActionType.DELETE},
        risky_actions={SafetyActionType.SUBMIT, SafetyActionType.DELETE}
    )
    guardrails = SafetyGuardrails(policy)
    
    # Safe action - no confirmation needed
    assert guardrails.should_require_confirmation(SafetyActionType.CLICK) is False
    
    # Risky action - confirmation needed
    assert guardrails.should_require_confirmation(SafetyActionType.SUBMIT) is True
    assert guardrails.should_require_confirmation(SafetyActionType.DELETE) is True
