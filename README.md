# Computer-Use Automation System

A complete implementation of a computer-use automation system for Interface.ai take-home project. This system uses an LLM to discover how to accomplish goals in legacy applications, then records the flow as a structured, deterministic capability that can be replayed without LLM involvement.

## Overview

This system addresses the challenge of automating legacy bank applications that have no API - the only way in is to drive the UI the way a human operator would. The system:

1. **Discovers**: Uses an LLM to figure out how to accomplish a goal by driving a real application
2. **Records**: Saves the successful run as a structured, typed, versioned artifact
3. **Replays**: Executes the artifact deterministically without LLM decision-making
4. **Escalates**: Provides human-in-the-loop handoff when stuck
5. **Protects**: Enforces safety guardrails and redacts sensitive data

## Architecture

The system is built with a clean separation of concerns:

- **Core**: Data models (artifact schema) and surface abstraction (web/desktop/legacy)
- **Agent**: LLM-driven discovery loop (observe → decide → act)
- **Replay**: Deterministic execution engine with error handling
- **Safety**: Allowlist enforcement, risk assessment, sensitive data redaction
- **Evidence**: Structured logging and evidence collection
- **Handoff**: Human-in-the-loop escalation and session transfer

## Setup

### Prerequisites

- Python 3.10 or higher
- OpenAI API key (or compatible LLM provider)
- Node.js (for Playwright browser automation)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd interfaceai-assignment
```

2. Install dependencies:
```bash
pip install -e .
playwright install chromium
```

3. Configure environment:
```bash
cp .env.example .env
```

4. Edit `.env` and add your OpenAI API key:
```bash
OPENAI_API_KEY=your_actual_api_key_here
```

### Target Application

The system includes a local "legacy bank admin console" that mimics real bank applications with:
- Table-based layouts
- No test IDs
- Dynamic element IDs
- Multi-step flows (member lookup → account details → update balance)

Start the target application:
```bash
python -m src.main start-target-app
```

The app will be available at `http://localhost:5000`

## Demo

The fastest way to see the system in action:

```bash
# Terminal 1: Start the target application
python -m src.main start-target-app

# Terminal 2: Run the complete demo
python -m src.main demo
```

The demo will:
1. Run discovery to learn how to look up a member and read their balance
2. Save the capability artifact
3. Replay the artifact deterministically
4. Replay with an error scenario to demonstrate error handling

## Usage

### Discovery

Discover how to accomplish a goal:

```bash
python -m src.main discover "Look up member 12345 and read their current savings balance" \
    --target-url http://localhost:5000 \
    --output artifact.json \
    --evidence-dir evidence/discovery
```

Options:
- `--target-url`: URL of the target application (default: from .env)
- `--headless`: Run browser in headless mode (default: true)
- `--output`: Output file for the artifact (default: artifact.json)
- `--evidence-dir`: Directory for evidence (screenshots, logs)

### Replay

Replay a saved artifact:

```bash
python -m src.main replay artifact.json \
    --member-id 12345 \
    --evidence-dir evidence/replay
```

Options:
- `--member-id`: Member ID parameter (if the artifact requires it)
- `--headless`: Run browser in headless mode (default: true)
- `--evidence-dir`: Directory for evidence

## Testing

Run the test suite:

```bash
pytest tests/
```

Tests cover:
- Core data models and serialization
- Safety guardrails and sensitive data redaction
- Evidence collection and logging

## Project Structure

```
interfaceai-assignment/
├── src/
│   ├── core/           # Data models and surface abstraction
│   ├── agent/          # LLM-driven discovery
│   ├── replay/         # Deterministic replay engine
│   ├── safety/         # Guardrails and redaction
│   ├── evidence/       # Logging and evidence collection
│   ├── handoff/        # Human-in-the-loop coordination
│   ├── target_app/     # Legacy-like bank admin console
│   ├── config.py       # Configuration management
│   └── main.py         # CLI entry point
├── tests/              # Test suite
├── evidence/           # Evidence from runs (generated)
├── pyproject.toml      # Python project configuration
├── .env.example        # Environment template
├── README.md           # This file
└── REPORT.md           # Design write-up
```

## Key Design Decisions

### Surface Abstraction
The artifact schema and replay logic are surface-agnostic. The `SurfaceInterface` abstracts "observe state" and "perform action" operations, allowing the same artifacts to work across web, legacy web, and desktop applications.

### Locator Strategy
For legacy applications without test IDs, the system prioritizes:
1. Text-based locators (visible text is usually stable)
2. Accessibility tree (more stable than raw DOM)
3. CSS/XPath selectors with fallbacks

### Error Taxonomy
The system distinguishes three types of failures:
- **Business outcomes**: Expected results (e.g., "member not found")
- **Recoverable conditions**: Transient issues (e.g., session timeout)
- **Hard failures**: Unrecoverable errors (e.g., element not found)

### Safety Model
- Allowlist enforcement for domains and action types
- Risk assessment (safe/reversible/risky/irreversible)
- Automatic redaction of sensitive data (SSN, credit cards, API keys, etc.)
- Confirmation requirements for risky actions

## Evidence and Observability

Every run generates structured evidence in the `evidence/` directory:
- `metadata.json`: Session metadata and final status
- `log.jsonl`: Line-by-line log of all actions and decisions
- `log_consolidated.json`: Consolidated log in JSON format
- `result.json`: Execution result with outputs or error details
- `error.json`: Detailed error information (if failed)
- `step_*.png`: Screenshots at each step
- `state_*.json`: State snapshots at key points

All sensitive data is automatically redacted from evidence.

## Human-in-the-Loop

When the system encounters a condition it cannot handle:
1. It detects the stuck/blocked state
2. Raises an intervention request with context
3. Pauses automation and exposes the live session
4. Allows human manual control
5. Captures what the human did
6. Resumes automation from the current state

The CLI provides a minimal but real handoff mechanism. A production system would integrate with an operator console.

## Extensibility

### Multi-Tenant Reuse
The artifact schema is designed to support reuse across tenants running the same vendor application:
- Parameters capture tenant-specific values (IDs, URLs)
- Locators use semantic strategies (text, role) rather than brittle selectors
- Version tracking allows for drift detection and updates

### Desktop Applications
The `DesktopSurface` class (placeholder) shows how to extend to desktop applications using OS-level automation frameworks (UI Automation, Accessibility API, etc.). The artifact schema doesn't need to change.

## Limitations and Future Work

See the [REPORT.md](REPORT.md) for detailed discussion of:
- Design trade-offs
- What was intentionally omitted
- What would be built next with more time

## License

This is a take-home project submission for Interface.ai.
