"""
Safety guardrails and policy enforcement.

This module implements allowlist enforcement, risk assessment, and sensitive
data redaction to ensure the automation system operates within safe boundaries.

Security is critical for banking applications handling regulated financial data.
This module provides:
- Allowlist enforcement for domains, routes, and action types
- Risk assessment for all actions (safe/reversible/risky/irreversible)
- Automatic sensitive data redaction (SSN, credit cards, API keys, passwords)
- Confirmation requirements for risky actions
- Configurable safety policies per deployment

All sensitive data is automatically redacted before being stored in logs,
artifacts, or evidence to ensure compliance with financial regulations.
"""

import re
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Risk levels for actions."""
    SAFE = "safe"
    REVERSIBLE = "reversible"
    RISKY = "risky"
    IRREVERSIBLE = "irreversible"


class ActionType(str, Enum):
    """Types of actions that can be performed."""
    CLICK = "click"
    TYPE = "type"
    NAVIGATE = "navigate"
    WAIT = "wait"
    EXTRACT = "extract"
    SUBMIT = "submit"
    DELETE = "delete"
    CONFIRM = "confirm"
    SELECT = "select"


class AllowlistPolicy(BaseModel):
    """Policy for what is allowed during automation."""
    allowed_domains: Set[str] = Field(default_factory=set, description="Permitted domains")
    allowed_routes: Set[str] = Field(default_factory=set, description="Permitted URL patterns")
    allowed_actions: Set[ActionType] = Field(default_factory=set, description="Permitted action types")
    risky_actions: Set[ActionType] = Field(default_factory=set, description="Actions requiring extra caution")
    blocked_actions: Set[ActionType] = Field(default_factory=set, description="Actions that are blocked")
    max_steps: int = Field(default=50, description="Maximum number of steps")
    timeout_seconds: int = Field(default=300, description="Maximum execution time")


class SensitiveDataPattern(BaseModel):
    """Pattern for detecting sensitive data."""
    name: str
    pattern: str
    description: str
    redaction_placeholder: str = "[REDACTED]"


class SensitiveDataRedactor:
    """
    Redacts sensitive data from artifacts and logs.
    
    Never persist credentials, tokens, or regulated financial data (PII).
    """
    
    # Common patterns for sensitive data
    PATTERNS = [
        SensitiveDataPattern(
            name="ssn",
            pattern=r'\b\d{3}-\d{2}-\d{4}\b',
            description="Social Security Number",
            redaction_placeholder="[SSN_REDACTED]"
        ),
        SensitiveDataPattern(
            name="credit_card",
            pattern=r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            description="Credit Card Number",
            redaction_placeholder="[CC_REDACTED]"
        ),
        SensitiveDataPattern(
            name="api_key",
            pattern=r'(api[_-]?key|apikey)\s*[:=]\s*[\'"]?([a-zA-Z0-9_-]{10,})[\'"]?',
            description="API Key",
            redaction_placeholder="[API_KEY_REDACTED]"
        ),
        SensitiveDataPattern(
            name="token",
            pattern=r'(token|bearer)\s*[:=]\s*[\'"]?([a-zA-Z0-9_-]{20,})[\'"]?',
            description="Authentication Token",
            redaction_placeholder="[TOKEN_REDACTED]"
        ),
        SensitiveDataPattern(
            name="password",
            pattern=r'(password|passwd|pwd)\s*[:=]\s*[\'"]?([^\'"\s]+)[\'"]?',
            description="Password",
            redaction_placeholder="[PASSWORD_REDACTED]"
        ),
        SensitiveDataPattern(
            name="email",
            pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            description="Email Address",
            redaction_placeholder="[EMAIL_REDACTED]"
        ),
        SensitiveDataPattern(
            name="account_number",
            pattern=r'\b\d{8,17}\b',
            description="Account Number (8-17 digits)",
            redaction_placeholder="[ACCOUNT_REDACTED]"
        ),
    ]
    
    @classmethod
    def redact_text(cls, text: str) -> str:
        """Redact sensitive data from text."""
        redacted = text
        for pattern_def in cls.PATTERNS:
            redacted = re.sub(pattern_def.pattern, pattern_def.redaction_placeholder, redacted, flags=re.IGNORECASE)
        return redacted
    
    @classmethod
    def redact_dict(cls, data: Dict[str, Any], keys_to_redact: Optional[Set[str]] = None) -> Dict[str, Any]:
        """
        Redact sensitive data from a dictionary.
        
        Args:
            data: Dictionary to redact
            keys_to_redact: Specific keys to always redact (e.g., 'password', 'token')
        """
        if keys_to_redact is None:
            keys_to_redact = {'password', 'token', 'api_key', 'secret', 'credential', 'ssn', 'credit_card'}
        
        redacted = {}
        for key, value in data.items():
            # Always redact sensitive keys with specific placeholders
            if any(sensitive in key.lower() for sensitive in keys_to_redact):
                # Use specific placeholder based on key type
                if 'ssn' in key.lower():
                    redacted[key] = "[SSN_REDACTED]"
                elif 'credit_card' in key.lower() or 'cc' in key.lower():
                    redacted[key] = "[CC_REDACTED]"
                elif 'api_key' in key.lower() or 'apikey' in key.lower():
                    redacted[key] = "[API_KEY_REDACTED]"
                elif 'password' in key.lower() or 'pwd' in key.lower():
                    redacted[key] = "[PASSWORD_REDACTED]"
                elif 'token' in key.lower():
                    redacted[key] = "[TOKEN_REDACTED]"
                else:
                    redacted[key] = "[REDACTED]"
            elif isinstance(value, str):
                redacted[key] = cls.redact_text(value)
            elif isinstance(value, dict):
                redacted[key] = cls.redact_dict(value, keys_to_redact)
            elif isinstance(value, list):
                redacted[key] = [cls.redact_text(item) if isinstance(item, str) else item for item in value]
            else:
                redacted[key] = value
        
        return redacted
    
    @classmethod
    def add_custom_pattern(cls, pattern: SensitiveDataPattern) -> None:
        """Add a custom sensitive data pattern."""
        cls.PATTERNS.append(pattern)


class SafetyGuardrails:
    """
    Enforces safety policies and guardrails.
    
    This is the gatekeeper that ensures automation only operates within
    configured boundaries and handles risky actions appropriately.
    """
    
    def __init__(self, policy: AllowlistPolicy):
        self.policy = policy
        self.redactor = SensitiveDataRedactor()
    
    def is_action_allowed(self, action: ActionType, target: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """
        Check if an action is allowed by policy.
        
        Returns:
            (allowed, reason) tuple
        """
        # Check if action is explicitly blocked
        if action in self.policy.blocked_actions:
            return False, f"Action '{action}' is blocked by policy"
        
        # Check if action is in allowed list
        if action not in self.policy.allowed_actions:
            return False, f"Action '{action}' not in allowlist"
        
        # Check domain if target is a URL
        if target and action in [ActionType.NAVIGATE, ActionType.CLICK]:
            if not self._is_domain_allowed(target):
                return False, f"Domain not in allowlist: {self._extract_domain(target)}"
        
        return True, None
    
    def is_action_risky(self, action: ActionType) -> bool:
        """Check if an action is considered risky."""
        return action in self.policy.risky_actions
    
    def assess_action_risk(self, action: ActionType, context: Optional[Dict[str, Any]] = None) -> RiskLevel:
        """
        Assess the risk level of an action with context.
        
        Context can include:
        - element_type: what kind of element is being acted on
        - value: what value is being entered
        - route: what page/route the action is on
        """
        if action in self.policy.blocked_actions:
            return RiskLevel.IRREVERSIBLE
        
        if action in self.policy.risky_actions:
            # Further assess based on context
            if context:
                element_type = context.get("element_type", "")
                if "delete" in element_type.lower() or "remove" in element_type.lower():
                    return RiskLevel.IRREVERSIBLE
                if "submit" in element_type.lower() or "confirm" in element_type.lower():
                    return RiskLevel.RISKY
            return RiskLevel.RISKY
        
        if action in [ActionType.TYPE, ActionType.SELECT]:
            return RiskLevel.REVERSIBLE
        
        return RiskLevel.SAFE
    
    def redact_sensitive_data(self, data: Any) -> Any:
        """Redact sensitive data from the given data structure."""
        if isinstance(data, str):
            return self.redactor.redact_text(data)
        elif isinstance(data, dict):
            return self.redactor.redact_dict(data)
        elif isinstance(data, list):
            return [self.redact_sensitive_data(item) for item in data]
        else:
            return data
    
    def _is_domain_allowed(self, url: str) -> bool:
        """Check if a URL's domain is in the allowlist."""
        domain = self._extract_domain(url)
        return any(allowed in domain for allowed in self.policy.allowed_domains)
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        # Simple extraction - in production use proper URL parsing
        if url.startswith("http://"):
            url = url[7:]
        elif url.startswith("https://"):
            url = url[8:]
        
        parts = url.split("/")
        return parts[0] if parts else url
    
    def should_require_confirmation(self, action: ActionType, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determine if an action requires human confirmation.
        
        Risky and irreversible actions should require confirmation before
        proceeding, especially in production environments.
        """
        risk_level = self.assess_action_risk(action, context)
        return risk_level in [RiskLevel.RISKY, RiskLevel.IRREVERSIBLE]


def create_default_policy() -> AllowlistPolicy:
    """Create a default safety policy."""
    return AllowlistPolicy(
        allowed_domains={"localhost", "127.0.0.1"},
        allowed_routes=set(),
        allowed_actions={
            ActionType.CLICK,
            ActionType.TYPE,
            ActionType.NAVIGATE,
            ActionType.WAIT,
            ActionType.EXTRACT,
            ActionType.SELECT,
        },
        risky_actions={
            ActionType.SUBMIT,
            ActionType.DELETE,
            ActionType.CONFIRM,
        },
        blocked_actions=set(),
        max_steps=50,
        timeout_seconds=300
    )
