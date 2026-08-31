"""
Evidence collection and structured logging.

This module handles the collection and storage of evidence for debugging and
auditability of automation runs.
"""

import json
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict

from ..core.models import ExecutionResult, SessionContext
from ..safety.guardrails import SensitiveDataRedactor


@dataclass
class LogEntry:
    """A single log entry."""
    timestamp: str
    level: str  # info, warning, error
    step: Optional[int]
    message: str
    details: Optional[Dict[str, Any]] = None


class EvidenceCollector:
    """
    Collects and stores evidence from automation runs.
    
    Evidence includes:
    - Structured logs of all actions and decisions
    - Screenshots at key points
    - State snapshots
    - Error details
    - Execution traces
    """
    
    def __init__(self, base_dir: str = "evidence"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.redactor = SensitiveDataRedactor()
        self.current_logs: List[LogEntry] = []
        self.current_session: Optional[str] = None
    
    def start_session(self, session_id: str, execution_type: str) -> None:
        """Start a new evidence collection session."""
        self.current_session = session_id
        self.current_logs = []
        
        session_dir = self.base_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Create metadata file
        metadata = {
            "session_id": session_id,
            "execution_type": execution_type,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "started"
        }
        
        metadata_path = session_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        self.log("info", None, f"Started {execution_type} session", {"session_id": session_id})
    
    def log(
        self,
        level: str,
        step: Optional[int],
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a log entry."""
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            step=step,
            message=message,
            details=details
        )
        
        self.current_logs.append(entry)
        
        # Also write to file immediately for durability
        if self.current_session:
            self._write_log_entry(entry)
    
    def _write_log_entry(self, entry: LogEntry) -> None:
        """Write a log entry to the session log file."""
        session_dir = self.base_dir / self.current_session
        log_file = session_dir / "log.jsonl"
        
        # Redact sensitive data
        entry_dict = asdict(entry)
        if entry_dict["details"]:
            entry_dict["details"] = self.redactor.redact_dict(entry_dict["details"])
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(entry_dict) + "\n")
    
    def save_screenshot(self, step: Optional[int], screenshot_bytes: bytes) -> str:
        """Save a screenshot."""
        if not self.current_session:
            return ""
        
        session_dir = self.base_dir / self.current_session
        timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
        filename = f"screenshot_{step or 'init'}_{timestamp}.png"
        path = session_dir / filename
        
        with open(path, 'wb') as f:
            f.write(screenshot_bytes)
        
        self.log("info", step, f"Screenshot saved", {"path": str(path)})
        return str(path)
    
    def save_state_snapshot(self, step: Optional[int], state: Dict[str, Any]) -> None:
        """Save a state snapshot."""
        if not self.current_session:
            return
        
        session_dir = self.base_dir / self.current_session
        timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
        filename = f"state_{step or 'init'}_{timestamp}.json"
        path = session_dir / filename
        
        # Redact sensitive data
        redacted_state = self.redactor.redact_dict(state)
        
        with open(path, 'w') as f:
            json.dump(redacted_state, f, indent=2)
        
        self.log("info", step, f"State snapshot saved", {"path": str(path)})
    
    def save_error(self, step: Optional[int], error: Dict[str, Any]) -> None:
        """Save error details."""
        if not self.current_session:
            return
        
        session_dir = self.base_dir / self.current_session
        error_file = session_dir / "error.json"
        
        # Redact sensitive data
        redacted_error = self.redactor.redact_dict(error)
        
        with open(error_file, 'w') as f:
            json.dump(redacted_error, f, indent=2)
        
        self.log("error", step, f"Error occurred", error)
    
    def finish_session(self, result: ExecutionResult) -> None:
        """Finish the current session and save final results."""
        if not self.current_session:
            return
        
        session_dir = self.base_dir / self.current_session
        
        # Update metadata
        metadata_path = session_dir / "metadata.json"
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        metadata["status"] = result.status
        metadata["finished_at"] = datetime.now(timezone.utc).isoformat()
        metadata["execution_time_seconds"] = result.execution_time_seconds
        metadata["steps_executed"] = result.steps_executed
        
        if result.status == "failure":
            metadata["error_type"] = result.error_type
            metadata["error_message"] = result.error_message
            metadata["failed_step"] = result.failed_step
        
        # Handle business outcomes
        if result.status == "business_outcome":
            metadata["business_outcome"] = result.business_outcome
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Save execution result
        result_path = session_dir / "result.json"
        result_dict = result.model_dump_json_safe()
        # Redact sensitive data
        result_dict = self.redactor.redact_dict(result_dict)
        
        with open(result_path, 'w') as f:
            json.dump(result_dict, f, indent=2)
        
        # Save consolidated log
        log_path = session_dir / "log_consolidated.json"
        with open(log_path, 'w') as f:
            json.dump([asdict(entry) for entry in self.current_logs], f, indent=2)
        
        self.log("info", None, f"Session finished with status: {result.status}")
        
        self.current_session = None
        self.current_logs = []
    
    def get_session_path(self, session_id: str) -> Path:
        """Get the path for a session."""
        return self.base_dir / session_id
    
    def list_sessions(self) -> List[str]:
        """List all session IDs."""
        if not self.base_dir.exists():
            return []
        return [d.name for d in self.base_dir.iterdir() if d.is_dir()]


class StructuredLogger:
    """
    Provides structured logging for the automation system.
    
    This is a simpler interface for logging that integrates with
    the EvidenceCollector.
    """
    
    def __init__(self, evidence_collector: EvidenceCollector):
        self.evidence = evidence_collector
    
    def info(self, step: Optional[int], message: str, **kwargs) -> None:
        """Log an info message."""
        self.evidence.log("info", step, message, kwargs or None)
    
    def warning(self, step: Optional[int], message: str, **kwargs) -> None:
        """Log a warning message."""
        self.evidence.log("warning", step, message, kwargs or None)
    
    def error(self, step: Optional[int], message: str, **kwargs) -> None:
        """Log an error message."""
        self.evidence.log("error", step, message, kwargs or None)
    
    def action(self, step: int, action_type: str, description: str, **kwargs) -> None:
        """Log an action."""
        self.evidence.log("info", step, f"Action: {action_type}", {
            "description": description,
            **kwargs
        })
    
    def decision(self, step: int, decision: str, reasoning: str, **kwargs) -> None:
        """Log a decision."""
        self.evidence.log("info", step, f"Decision: {decision}", {
            "reasoning": reasoning,
            **kwargs
        })
    
    def checkpoint(self, step: int, condition: str, passed: bool, **kwargs) -> None:
        """Log a checkpoint verification."""
        self.evidence.log("info" if passed else "warning", step, f"Checkpoint: {condition}", {
            "passed": passed,
            **kwargs
        })
