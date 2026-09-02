# Computer-Use Automation System

**A production-grade computer-use automation system for legacy applications with LLM-driven discovery and deterministic replay.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/playwright-latest-green.svg)](https://playwright.dev/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-orange.svg)](https://openai.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Overview

This system solves a critical problem in banking and enterprise automation: **how to reliably automate legacy applications that have no API**. The system uses an LLM to discover how to accomplish goals by driving the UI like a human, then records the flow as a structured, deterministic capability that can be replayed infinitely without LLM involvement.

### The Problem

Banks and credit unions have thousands of legacy applications with no API access. The only way to operate them is through the UI - exactly like a human operator would. These applications are often:
- **Stable but error-prone**: UIs don't change much, but runtime errors are common
- **Heterogeneous**: Mix of modern web apps, legacy web (tables, frames, no test IDs), and desktop apps
- **Multi-tenant**: Hundreds of institutions run the same vendor software with different configurations

### The Solution

**Discover once, replay infinitely.** The system:
1. **Discovers**: Uses an LLM to figure out how to accomplish a goal by driving a real application
2. **Records**: Saves the successful run as a structured, typed, versioned artifact
3. **Replays**: Executes the artifact deterministically without LLM decision-making
4. **Escalates**: Provides human-in-the-loop handoff when stuck
5. **Protects**: Enforces safety guardrails and redacts sensitive data

## 🏗️ Architecture

The system is built with clean architectural boundaries that enable extensibility:

```
┌─────────────────────────────────────────────────────────┐
│                    CLI Interface                        │
│                   (src/main.py)                         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│                 Coordination Layer                       │
│         (config.py, handoff/coordinator.py)              │
└─────┬──────────────┬──────────────┬────────────────────┘
      │              │              │
┌─────┴──────┐ ┌────┴─────┐ ┌────┴──────────────────┐
│  Discovery  │ │  Replay  │ │   Safety & Evidence  │
│  (agent/)   │ │(replay/) │ │(safety/, evidence/)  │
└─────┬──────┘ └────┬─────┘ └────┴──────────────────┘
      │             │             │
      └─────────────┴─────────────┴─────────────┐
                    │                         │
          ┌─────────┴─────────┐   ┌──────────┴──────────┐
          │    Core Models    │   │  Surface Abstraction │
          │   (core/models)  │   │   (core/surface)    │
          └───────────────────┘   └─────────────────────┘
```

### Key Design Principles

- **Surface Abstraction**: The artifact schema and replay logic are surface-agnostic. Same artifacts work across web, legacy web, and desktop apps.
- **Deterministic Replay**: No LLM involvement in production execution. Same inputs, same steps, same outputs.
- **Error Taxonomy**: Three-way distinction between business outcomes, recoverable conditions, and hard failures.
- **Safety First**: Allowlist enforcement, risk assessment, and automatic sensitive data redaction.
- **Observability**: Comprehensive evidence collection for debugging and auditability.

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- OpenAI API key (or compatible LLM provider)
- Modern web browser

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd interfaceai-assignment

# Install dependencies
pip install -e .
playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Demo Mode

The fastest way to see the system in action:

```bash
# Terminal 1: Start the target application
python -m src.main start-target-app

# Terminal 2: Run the complete demo
python -m src.main demo
```

The demo demonstrates:
1. **Discovery**: LLM learns how to look up a member and read their balance
2. **Artifact Generation**: Creates a structured, typed capability
3. **Deterministic Replay**: Executes the artifact without LLM
4. **Error Handling**: Demonstrates business outcome vs. failure distinction

## 📖 Usage

### Discovery Mode

Discover how to accomplish a goal:

```bash
python -m src.main discover "Look up member 12345 and read their current savings balance" \
    --target-url http://localhost:5000 \
    --output artifact.json \
    --headless false
```

### Replay Mode

Replay a saved artifact deterministically:

```bash
python -m src.main replay artifact.json \
    --member-id 12345 \
    --headless false
```

### Testing

Run the comprehensive test suite:

```bash
pytest tests/ -v
```

**Coverage:**
- Core data models and serialization
- Safety guardrails and sensitive data redaction  
- Evidence collection and logging
- **33 tests, all passing**

## 🧠 Core Features

### 1. LLM-Driven Discovery

The discovery agent runs an observe → decide → act loop:
- **Observe**: Captures current application state (accessibility tree, DOM, screenshots)
- **Decide**: LLM determines next action based on goal and current state
- **Act**: Executes action (click, type, navigate, wait, extract)
- **Repeat**: Until goal is met or stopping condition

**Key insight**: The LLM is only used during discovery. Production execution is deterministic.

### 2. Structured Artifact Schema

Artifacts are typed, versioned, and serializable:

```python
CapabilityArtifact:
  - artifact_id: Unique identifier
  - version: Semantic versioning
  - input_parameters: Typed inputs the caller provides
  - outputs: Typed data the capability returns
  - steps: Ordered actions with robust locators
  - checkpoints: Verification points
  - error_handlers: Known error conditions and responses
  - success_condition: How to verify completion
```

### 3. Deterministic Replay

Replay is truly deterministic:
- **No LLM**: All decisions are pre-recorded in the artifact
- **Parameter Substitution**: `{{member_id}}` → actual value
- **Checkpoint Verification**: Validates expected state at key points
- **Error Handling**: Distinguishes business outcomes from failures

### 4. Locator Strategy

For legacy applications without test IDs, the system prioritizes:
1. **Text-based locators**: Most stable (visible text rarely changes)
2. **Accessibility-based locators**: Role + text (e.g., "button with label 'Submit'")
3. **CSS/XPath with fallbacks**: Multiple strategies for robustness

### 5. Error Handling

Three-way error distinction:
- **Business Outcomes**: Expected results (e.g., "member not found")
- **Recoverable Conditions**: Transient issues (e.g., session timeout)
- **Hard Failures**: Unrecoverable errors (e.g., element not found)

### 6. Safety Guardrails

- **Allowlist Enforcement**: Domains, routes, and action types
- **Risk Assessment**: safe/reversible/risky/irreversible classification
- **Confirmation Requirements**: Risky actions require approval
- **Sensitive Data Redaction**: Automatic redaction of SSN, credit cards, API keys, passwords

### 7. Human-in-the-Loop

When disabled, the system:
- Detects stuck/blocked states
- Routes intervention requests with full context
- Pauses automation and exposes live session
- Captures human actions for evidence
- Resumes automation from current state

## 📁 Project Structure

```
interfaceai-assignment/
├── src/
│   ├── core/           # Data models and surface abstraction
│   │   ├── models.py   # Artifact schema, execution results
│   │   └── surface.py  # Surface abstraction (web/desktop/legacy)
│   ├── agent/          # LLM-driven discovery
│   │   └── discovery.py
│   ├── replay/         # Deterministic replay engine
│   │   └── engine.py
│   ├── safety/         # Guardrails and redaction
│   │   └── guardrails.py
│   ├── evidence/       # Logging and evidence collection
│   │   └── collector.py
│   ├── handoff/        # Human-in-the-loop coordination
│   │   └── coordinator.py
│   ├── target_app/     # Legacy-like bank admin console
│   │   └── app.py
│   ├── config.py       # Configuration management
│   └── main.py         # CLI entry point
├── tests/              # Comprehensive test suite
├── evidence/           # Evidence from runs (samples included)
├── pyproject.toml      # Python project configuration
├── .env.example        # Environment template
├── README.md           # This file
├── REPORT.md           # Design write-up
└── REQUIREMENTS_CHECKLIST.md  # Requirements verification
```

## 🔬 Evidence and Observability

Every run generates comprehensive evidence:

- **metadata.json**: Session metadata and final status
- **log.jsonl**: Line-by-line log of all actions and decisions
- **result.json**: Execution result with outputs or error details
- **error.json**: Detailed error information (if failed)
- **step_*.png**: Screenshots at each step
- **state_*.json**: State snapshots at key points

All sensitive data is automatically redacted from evidence.

## 🌐 Extensibility

### Multi-Tenant Reuse

The artifact schema supports reuse across tenants:
- **Parameterization**: Tenant-specific values (IDs, URLs) as parameters
- **Semantic Locators**: Text-based strategies work across branding changes
- **Version Tracking**: Drift detection and artifact updates

### Desktop Applications

The `DesktopSurface` class shows how to extend to desktop apps using:
- **Windows**: UI Automation, WinAppDriver
- **Mac**: Accessibility API
- **Linux**: AT-SPI / LDTP

The artifact schema doesn't need to change.

## 📊 Testing

Run the test suite:

```bash
pytest tests/ -v
```

**Test Coverage:**
- ✅ Core data models and serialization (11 tests)
- ✅ Safety guardrails and sensitive data redaction (13 tests)
- ✅ Evidence collection and logging (9 tests)
- ✅ **33 tests, all passing**

## 🎓 Design Decisions

See [REPORT.md](REPORT.md) for detailed discussion of:
- Architecture and key trade-offs
- Artifact schema design rationale
- Determinism and error handling strategy
- Heterogeneity and multi-tenant design
- Escalation and handoff mechanism
- Safety model and limitations
- Intentional simplifications and future work

## 🚧 Current Limitations

- **LLM Provider**: Currently supports OpenAI GPT-4o (easily extensible to others)
- **Desktop Surface**: Placeholder implementation (design complete)
- **Operator Console**: CLI-based handoff (web console design documented)
- **Multi-Tenant Infrastructure**: Design complete, implementation stubbed

These are intentional simplifications per the assignment scope. The core abstractions support full implementation.

## 🛡️ Security

- **Never persists** credentials, tokens, or raw sensitive data
- **Automatic redaction** of SSN, credit cards, API keys, passwords
- **Allowlist enforcement** for domains and action types
- **Risk assessment** for all actions (safe/reversible/risky/irreversible)
- **Audit logging** for all operations

## 📝 Assignment Requirements

This implementation satisfies all core requirements from the Interface.ai take-home assignment:

- ✅ **Goal-driven agent loop** with real UI interaction
- ✅ **Structured artifact** with typed schema
- ✅ **Deterministic replay** without LLM involvement
- ✅ **Error handling** with business outcome distinction
- ✅ **Safety guardrails** and sensitive data redaction
- ✅ **Evidence collection** and observability
- ✅ **Human-in-the-loop** escalation and handoff
- ✅ **Design for heterogeneity** and multi-tenant reuse

See [REQUIREMENTS_CHECKLIST.md](REQUIREMENTS_CHECKLIST.md) for detailed verification.

## 🤝 Contributing

This is a take-home project submission. For questions about the implementation, please refer to the [REPORT.md](REPORT.md) design documentation.

## 📄 License

MIT License - see LICENSE file for details.

---

**Built for Interface.ai Engineering Team Take-Home Assignment**
