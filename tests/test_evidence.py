"""
Tests for evidence collection and logging.
"""

import pytest
import json
from pathlib import Path
from src.evidence.collector import EvidenceCollector, StructuredLogger, LogEntry
from src.core.models import ExecutionResult


def test_evidence_collector_initialization():
    """Test EvidenceCollector initialization."""
    collector = EvidenceCollector(base_dir="test_evidence")
    
    assert collector.base_dir == Path("test_evidence")
    assert collector.current_session is None
    assert len(collector.current_logs) == 0


def test_evidence_collector_start_session():
    """Test starting a new session."""
    collector = EvidenceCollector(base_dir="test_evidence")
    
    collector.start_session("test_session", "discovery")
    
    assert collector.current_session == "test_session"
    assert len(collector.current_logs) == 1  # Initial log entry
    
    # Check that session directory was created
    session_dir = collector.base_dir / "test_session"
    assert session_dir.exists()
    
    # Check that metadata file was created
    metadata_file = session_dir / "metadata.json"
    assert metadata_file.exists()
    
    # Clean up
    import shutil
    shutil.rmtree("test_evidence")


def test_evidence_collector_log():
    """Test logging entries."""
    collector = EvidenceCollector(base_dir="test_evidence")
    collector.start_session("test_session", "discovery")
    
    collector.log("info", 1, "Test message", {"key": "value"})
    
    assert len(collector.current_logs) == 2  # Initial + new log
    
    last_log = collector.current_logs[-1]
    assert last_log.level == "info"
    assert last_log.step == 1
    assert last_log.message == "Test message"
    assert last_log.details == {"key": "value"}
    
    # Clean up
    import shutil
    shutil.rmtree("test_evidence")


def test_evidence_collector_finish_session():
    """Test finishing a session."""
    collector = EvidenceCollector(base_dir="test_evidence")
    collector.start_session("test_session", "discovery")
    
    result = ExecutionResult(
        artifact_id="test_artifact",
        execution_type="discovery",
        status="success",
        outputs={"balance": 1000},
        steps_executed=5,
        execution_time_seconds=2.5
    )
    
    collector.finish_session(result)
    
    assert collector.current_session is None
    assert len(collector.current_logs) == 0
    
    # Check that result file was created
    session_dir = collector.base_dir / "test_session"
    result_file = session_dir / "result.json"
    assert result_file.exists()
    
    # Check that consolidated log was created
    log_file = session_dir / "log_consolidated.json"
    assert log_file.exists()
    
    # Clean up
    import shutil
    shutil.rmtree("test_evidence")


def test_structured_logger():
    """Test StructuredLogger."""
    collector = EvidenceCollector(base_dir="test_evidence")
    logger = StructuredLogger(collector)
    
    collector.start_session("test_session", "discovery")
    
    logger.info(1, "Info message")
    logger.warning(2, "Warning message", detail="some detail")
    logger.error(3, "Error message", error_code=500)
    logger.action(4, "click", "Clicked button", selector="#btn")
    logger.decision(5, "navigate", "Need to go to next page", reason="form submitted")
    logger.checkpoint(6, "element_visible", True, element="#balance")
    
    assert len(collector.current_logs) == 7  # Initial + 6 logs
    
    # Clean up
    import shutil
    shutil.rmtree("test_evidence")


def test_log_entry_serialization():
    """Test that LogEntry can be serialized."""
    entry = LogEntry(
        timestamp="2024-01-01T00:00:00",
        level="info",
        step=1,
        message="Test message",
        details={"key": "value"}
    )
    
    from dataclasses import asdict
    serialized = asdict(entry)
    
    assert serialized["timestamp"] == "2024-01-01T00:00:00"
    assert serialized["level"] == "info"
    assert serialized["step"] == 1
    assert serialized["message"] == "Test message"
    assert serialized["details"] == {"key": "value"}


def test_evidence_collector_list_sessions():
    """Test listing sessions."""
    collector = EvidenceCollector(base_dir="test_evidence")
    
    collector.start_session("session1", "discovery")
    collector.finish_session(ExecutionResult(
        artifact_id="test",
        execution_type="discovery",
        status="success",
        steps_executed=1,
        execution_time_seconds=1.0
    ))
    
    collector.start_session("session2", "replay")
    collector.finish_session(ExecutionResult(
        artifact_id="test",
        execution_type="replay",
        status="success",
        steps_executed=1,
        execution_time_seconds=1.0
    ))
    
    sessions = collector.list_sessions()
    
    assert "session1" in sessions
    assert "session2" in sessions
    assert len(sessions) == 2
    
    # Clean up
    import shutil
    shutil.rmtree("test_evidence")
