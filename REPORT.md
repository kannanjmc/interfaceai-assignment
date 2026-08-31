# Design Report: Computer-Use Automation System

## 1. Architecture

### System Overview

The system is designed as a layered architecture with clear separation of concerns:

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
└─────┬──────┘ └────┬─────┘ └────┬──────────────────┘
      │             │             │
      └─────────────┴─────────────┴─────────────┐
                    │                         │
          ┌─────────┴─────────┐   ┌──────────┴──────────┐
          │    Core Models    │   │  Surface Abstraction │
          │   (core/models)  │   │   (core/surface)    │
          └───────────────────┘   └─────────────────────┘
```

### Key Architectural Decisions

**1. Surface Abstraction Layer**
The `SurfaceInterface` abstracts the underlying automation technology (Playwright, OS automation, etc.) behind a unified set of operations: `get_state()`, `find_element()`, `click()`, `type_text()`, etc. This is the critical seam that allows the same artifact schema and replay logic to work across web, legacy web, and desktop applications without modification.

*Trade-off*: Adds an abstraction layer, but enables cross-platform reuse and clean separation of concerns.

**2. Artifact-First Design**
The artifact schema (`CapabilityArtifact`) is the central data model. Discovery produces artifacts; replay consumes them. This is a "record once, replay many" model where the artifact is the source of truth for how a task is accomplished.

*Trade-off*: Requires careful schema design, but enables deterministic replay without LLM involvement.

**3. Single-Process Architecture**
The system runs as a single process (with async operations) rather than a distributed system of queues and workers.

*Trade-off*: Limits horizontal scaling, but simplifies development, testing, and local execution. Scaling can be added later by putting the replay engine behind a queue.

**4. Python with Playwright**
Chose Python for its strong automation ecosystem and Playwright for browser automation. Playwright provides good cross-browser support, accessibility tree access (critical for legacy apps), and headless operation.

*Trade-off*: Python async can be verbose, but the ecosystem and readability for reviewers outweigh this.

**5. OpenAI GPT-4o for Discovery**
Using GPT-4o for the LLM-driven discovery loop. It provides strong reasoning capabilities for multi-step tasks and good tool-use support.

*Trade-off*: Requires API costs, but a single discovery run is inexpensive (~$0.50-1.00) and the model is only used during discovery, not replay.

### Component Responsibilities

- **Core Models**: Define the artifact schema, execution results, and session context. These are the data contracts that everything else builds on.
- **Surface Abstraction**: Provide a unified interface for interacting with different application types (web, legacy web, desktop).
- **Discovery Agent**: Run the LLM-driven observe→decide→act loop to learn how to accomplish a goal.
- **Replay Engine**: Execute artifacts deterministically with parameter substitution, checkpoint verification, and error handling.
- **Safety Guardrails**: Enforce allowlists, assess risk, and redact sensitive data.
- **Evidence Collector**: Capture structured logs, screenshots, and state snapshots for debugging and auditability.
- **Handoff Coordinator**: Manage human-in-the-loop escalation and live session transfer.

## 2. Artifact Schema

### Schema Design Principles

The artifact schema is designed to be:
- **Typed**: Every field has a type for validation and IDE support
- **Versioned**: Semantic versioning for artifact evolution
- **Serializable**: JSON serialization for storage and transmission
- **Reviewable**: Human-readable descriptions for both developers and AI agents
- **Parameterized**: Input parameters allow reuse across different invocations
- **Independent**: Decoupled from the raw LLM transcript - it's the distilled capability

### Core Schema Structure

```python
CapabilityArtifact:
  # Metadata
  artifact_id: str              # Unique identifier
  version: str                  # Semantic version (e.g., "1.0.0")
  name: str                     # Human-readable name
  description: str              # Detailed description
  
  # Target information
  target_app: str               # Application URL/identifier
  target_type: str              # "web", "legacy_web", "desktop"
  
  # Contract
  input_parameters: List[ParameterDefinition]  # Inputs from caller
  outputs: List[OutputDefinition]              # Data returned to caller
  
  # The flow
  steps: List[ActionStep]       # Ordered actions to execute
  checkpoints: List[Checkpoint] # Verification points
  
  # Error handling
  error_handlers: List[ErrorHandling]  # Known error conditions
  
  # Success condition
  success_condition: Dict[str, Any]  # How to verify completion
  
  # Safety metadata
  risk_level: RiskLevel         # Overall risk assessment
  allowlist_tags: List[str]     # Policy tags
```

### ActionStep Design

Each step captures:
- **Action type**: click, type, navigate, wait, extract, submit, select
- **Locator strategy**: Primary locator + fallbacks with type (css, xpath, text, role_and_text, aria_label)
- **Risk level**: safe, reversible, risky, irreversible
- **Data extraction**: How to extract outputs if this step produces data
- **Error handling**: Known error patterns and recovery actions

### Locator Strategy

The locator design prioritizes robustness for legacy applications:

1. **Text-based locators**: Most stable - visible text rarely changes
2. **Accessibility-based locators**: Role + text (e.g., "button with label 'Submit'")
3. **CSS/XPath selectors**: Used as fallbacks, with multiple options
4. **Fallback chain**: If primary fails, try fallbacks in order

This reflects the reality of legacy bank apps where test IDs don't exist and DOM structures can be fragile.

### Parameter and Output Definitions

**Input parameters** define the contract for invoking the capability:
- `name`: Parameter identifier
- `type`: Data type (string, number, boolean)
- `description`: Human-readable explanation
- `required`: Whether the parameter is mandatory
- `example`: Example value for documentation

**Outputs** define what data the capability returns:
- `name`: Output field name
- `type`: Data type
- `description`: What the output represents
- `locator`: How to extract this data from the UI

### Checkpoint Design

Checkpoints verify that the expected state was reached:
- Associated with specific steps
- Define conditions (element visible, URL contains, text present)
- Can specify business outcomes on failure (e.g., "member_not_found")

This distinguishes between "step failed" (technical error) and "business outcome" (expected result).

### Error Handling Schema

Error handlers define known exceptional states:
- `error_pattern`: Pattern to match (error message, condition)
- `outcome_type`: "business_outcome", "recoverable", or "hard_failure"
- `outcome_value`: Specific outcome for business outcomes
- `recovery_action`: How to recover (for recoverable errors)

This three-way distinction is critical: business outcomes are not failures, recoverable errors can be handled automatically, and hard failures stop execution.

## 3. Determinism & Error Handling

### Achieving Determinism

**1. No LLM in Replay Path**
The replay engine never calls the LLM. Every decision is pre-recorded in the artifact. This is the core of determinism - same inputs always produce the same sequence of actions.

**2. Parameter Substitution**
Input parameters are substituted into the artifact before execution:
- Text values: `{{member_id}}` → `"12345"`
- URLs: `/member/{{member_id}}` → `/member/12345`
- Locators: Any parameterized values are resolved

**3. Explicit Waiting**
Rather than implicit waits, each step can specify explicit wait conditions:
- `element_visible`: Wait for an element to appear
- `text_present`: Wait for text to appear in the page
- `url_contains`: Wait for URL to match a pattern

This avoids flakiness from timing issues.

**4. Checkpoint Verification**
After key steps, checkpoints verify the expected state:
- Navigation checkpoints verify URL
- Content checkpoints verify element visibility
- Data checkpoints verify expected values

If a checkpoint fails, it's treated as an error condition.

### Error Detection and Classification

The system detects errors at three levels:

**1. Action Execution Errors**
- Element not found
- Element not clickable/visible
- Navigation failed
- Timeout waiting for condition

**2. Checkpoint Failures**
- Expected element not visible
- URL doesn't match expected pattern
- Expected text not present

**3. Known Error Conditions**
Pattern matching against the current state:
- "member not found" → business outcome
- "session expired" → recoverable (re-authenticate)
- "access denied" → hard failure

### Error Response Strategy

**Business Outcomes** (expected results, not failures):
- Example: "member not found", "insufficient funds"
- Response: Return with status `business_outcome` and the specific outcome
- Caller decides how to handle (inform user, retry, etc.)

**Recoverable Conditions** (transient issues):
- Example: session timeout, slow load, temporary error dialog
- Response: Execute recovery action (refresh, re-authenticate, dismiss dialog)
- Retry the step up to max attempts
- If recovery fails, escalate to hard failure

**Hard Failures** (unrecoverable errors):
- Example: element not found, permission denied, unexpected error
- Response: Stop execution immediately
- Return detailed error information (step, expected, observed)
- May trigger human escalation

### Handling UI Drift

While the assignment emphasizes that UIs are stable in the bank environment, the system has some defenses against drift:

1. **Fallback locators**: If primary selector fails, try alternatives
2. **Text-based locators**: Less susceptible to structural changes
3. **Accessibility tree**: More stable than raw DOM
4. **Error patterns**: Detect when the page structure has changed fundamentally
5. **Version tracking**: Artifacts are versioned; drift detection can trigger re-recording

For production, a drift detection system would:
- Monitor replay success rates
- Detect patterns of failures
- Flag artifacts for re-recording
- Support A/B testing of new artifact versions

## 4. Heterogeneity & Multi-Tenant

### Surface Abstraction for Heterogeneity

The `SurfaceInterface` abstracts the differences between surface types:

**Web Surface** (Modern web apps):
- Uses Playwright browser automation
- Leverages DOM selectors, accessibility tree
- Supports iframes, multiple tabs

**Legacy Web Surface** (Table-based, no test IDs):
- Extends WebSurface with legacy-friendly strategies
- Prioritizes text-based locators over CSS selectors
- Handles framesets and nested tables
- Uses accessibility tree as primary state source

**Desktop Surface** (Native applications):
- Placeholder implementation showing the seam
- Would use OS-level automation:
  - Windows: UI Automation, WinAppDriver
  - Mac: Accessibility API
  - Linux: AT-SPI / LDTP
- Same `SurfaceInterface` methods, different underlying technology

**Key Insight**: The artifact schema doesn't change. A capability recorded on a web app could, in principle, be replayed on a desktop app if the surface types are compatible (same action types, similar UI patterns). In practice, you'd record separate artifacts per surface type, but the learning and replay logic is identical.

### Multi-Tenant Reuse Design

**Problem**: Hundreds of tenants run ~20 apps each. Many run the same vendor product with different configurations, branding, and versions.

**Solution**: Design artifacts to be tenant-agnostic where possible:

**1. Parameterization**
- Tenant-specific values (URLs, IDs, branding text) are parameters
- Example: `{{tenant_url}}/members/{{member_id}}`
- Each tenant provides their parameter values at runtime

**2. Semantic Locators**
- Use role-based locators: "button with text 'Submit'"
- Avoid tenant-specific selectors: `#tenant-specific-submit-btn`
- Text that varies (branding) is parameterized

**3. Version Artifacts**
- Semantic versioning: `1.0.0`, `1.1.0`, `2.0.0`
- Track which app version each artifact supports
- Tenant metadata: which tenants/vendorses an artifact works for

**4. Override Mechanism**
- Base artifact for "standard" vendor configuration
- Per-tenant overrides for customizations:
  - Different locators for custom UI elements
  - Additional steps for tenant-specific workflows
  - Different error patterns for tenant-specific errors

**5. Drift Detection**
- Monitor replay success rates per tenant
- Detect when a tenant's app version has changed
- Flag artifacts for re-recording or validation
- Support automated regression testing across tenants

**Example Scenario**:
- Vendor "BankCore" used by 50 tenants
- Base artifact recorded on Tenant A's v2.1 instance
- Tenant B runs v2.1 with custom branding
- Tenant C runs v2.2 with UI changes
- System tracks artifact compatibility and can:
  - Replay base artifact on Tenant B (parameterized branding)
  - Flag Tenant C for re-recording (version mismatch)
  - Support Tenant-specific overrides for custom flows

**Trade-off**: Requires metadata and version tracking infrastructure, but avoids recording artifacts from scratch for each tenant.

## 5. Escalation & Handoff

### Detecting "Stuck" States

The system detects when automation is stuck through multiple signals:

**1. Consecutive Failures**
- Track consecutive step failures
- If `consecutive_failures >= threshold` (default: 3), escalate
- Indicates the agent is in a loop or unable to progress

**2. Specific Error Patterns**
- Security errors: "access denied", "unauthorized", "permission denied"
- System errors: "stuck", "deadlock", "hung"
- Unknown errors not in the error handler catalog

**3. Agent Self-Report**
- The LLM can signal it's stuck during discovery
- Sets `stuck: true` in its decision response
- Includes reasoning about why it can't proceed

**4. Timeout**
- Max steps exceeded
- Total execution time exceeded
- Individual step timeout

### Handoff Mechanism

The handoff process has four phases:

**Phase 1: Detection and Request**
- Escalation detector identifies stuck state
- Creates `InterventionRequest` with:
  - Session ID
  - Reason for escalation
  - Current step number
  - Current state/context
  - Evidence path (screenshots, logs)
- Saves request to evidence directory

**Phase 2: Pause and Prepare**
- Call `surface.pause_automation()`
- For web: Keep browser session alive, stop automated actions
- Expose session for manual control:
  - In production: Expose CDP endpoint to operator console
  - In this implementation: Console-based signal
- Update session state to `IN_HUMAN_CONTROL`

**Phase 3: Human Control**
- Human operator receives intervention request
- Accesses the live session (same browser, same state)
- Performs manual steps to resolve the issue
- System captures what the human did (for evidence)
- Human signals completion

**Phase 4: Resume**
- Human signals completion (via operator console or CLI)
- Call `surface.resume_automation()`
- Automation continues from current state
- Replay engine resumes from the step after handoff
- Human's actions are recorded in evidence

### Control Transfer Model

The system maintains explicit control state:

```python
session.controller = "automation" | "human"
session.state = "active" | "paused" | "handed_off" | "completed" | "failed"
```

**Key Design Principles**:
1. **Single Source of Truth**: The live session is the same throughout - no new session is created
2. **Explicit State**: Always know who/what is in control
3. **Context Preservation**: All evidence and state are preserved across handoff
4. **Audit Trail**: Human actions are recorded alongside automated actions

### Operator Console (Design)

The current implementation uses a CLI-based handoff for simplicity. A production operator console would provide:

**Features**:
- Real-time session preview (live screenshot/stream)
- Intervention request queue with context
- One-click session takeover
- Manual control tools (click, type, navigate)
- Annotation and note-taking
- Resolution recording
- Session resume signal

**Architecture**:
- WebSocket connection to browser session (CDP)
- Web-based operator interface
- Integration with intervention queue
- Authentication and authorization
- Audit logging

**Current Implementation**:
- CLI prompts for human intervention
- Browser session remains open
- Human can manually operate the browser
- Press Enter to signal completion
- Evidence captured automatically

**Trade-off**: CLI is sufficient to demonstrate the mechanism; production would need a proper web console for team operations.

## 6. Safety

### Guardrail Model

**1. Allowlist Enforcement**
- **Domain allowlist**: Only permit actions on configured domains
- **Action allowlist**: Only permit configured action types
- **Route allowlist**: (Optional) Restrict to specific URL patterns
- **Blocked actions**: Explicitly block dangerous actions

**Configuration**:
```python
allowed_domains = {"localhost", "127.0.0.1", "*.bank.com"}
allowed_actions = {CLICK, TYPE, NAVIGATE, WAIT, EXTRACT}
blocked_actions = {DELETE}
```

**Enforcement**: Every action is checked before execution. Violations are blocked and logged.

**2. Risk Assessment**
Actions are classified by risk level:
- **Safe**: Navigate, wait, extract - no state changes
- **Reversible**: Type, select - can be undone
- **Risky**: Submit, confirm - makes changes
- **Irreversible**: Delete - cannot be undone

**Risk-based handling**:
- Safe actions: Execute normally
- Reversible actions: Execute with logging
- Risky actions: Require confirmation or flag for review
- Irreversible actions: Block or require explicit approval

**3. Confirmation Requirements**
Risky and irreversible actions require human confirmation:
- During discovery: LLM prompted to confirm
- During replay: Configurable policy (block/warn/allow)
- Evidence: Confirmation events are logged

**4. Sensitive Data Redaction**
Never persist credentials, tokens, or regulated financial data:

**Patterns redacted**:
- SSN: `123-45-6789` → `[SSN_REDACTED]`
- Credit cards: `4111-1111-1111-1111` → `[CC_REDACTED]`
- API keys: `api_key: sk-xxx` → `[API_KEY_REDACTED]`
- Passwords: `password: xxx` → `[PASSWORD_REDACTED]`
- Emails: `user@example.com` → `[EMAIL_REDACTED]`
- Account numbers: 8-17 digits → `[ACCOUNT_REDACTED]`

**Where redaction is applied**:
- Artifacts (before saving)
- Logs (before writing)
- Evidence (screenshots masked if possible)
- Error messages
- Human handoff context

**Key-based redaction**: Any field with "password", "token", "secret", "credential" in the name is automatically redacted.

### Safety Limitations

**What's protected**:
- Actions outside allowlist are blocked
- Sensitive data is redacted from logs/artifacts
- Risky actions require confirmation
- Domain restrictions prevent unauthorized access

**What's not fully protected** (would require additional infrastructure):
- Authentication/authorization of human operators
- Encryption of evidence at rest
- Role-based access control to artifacts
- Audit log tamper protection
- Rate limiting to prevent abuse

**Production hardening** would add:
- Authentication for all API endpoints
- Encryption of sensitive evidence
- Immutable audit logs (WORM storage)
- RBAC for artifact access
- Rate limiting and quotas
- Security monitoring and alerting

## 7. Cuts

### Intentionally Omitted

**1. Full Operator Console**
- **What**: Real-time web-based operator interface with live session preview
- **Why**: Assignment explicitly says this is out of scope
- **Current**: CLI-based handoff that demonstrates the mechanism
- **Next**: Build React/TypeScript operator console with WebSocket connection to CDP

**2. Desktop Surface Implementation**
- **What**: Actual desktop automation using OS-level frameworks
- **Why**: Not required for the assignment; would require OS-specific testing
- **Current**: `DesktopSurface` placeholder showing the seam
- **Next**: Implement for Windows (UI Automation) and Mac (Accessibility API)

**3. Multi-Tenant Infrastructure**
- **What**: Tenant management, artifact catalog, version tracking, drift detection
- **Why**: Assignment requires design discussion, not implementation
- **Current**: Artifacts have version fields and parameterization support
- **Next**: Build tenant service, artifact registry, drift monitoring system

**4. Agent-Facing Capability Interface**
- **What**: API endpoint or tool-calling surface for AI agents to discover and invoke capabilities
- **Why**: Stretch goal; core functionality is more important
- **Current**: CLI interface for manual invocation
- **Next**: Build FastAPI endpoints with OpenAPI spec for agent integration

**5. Production Hardening**
- **What**: Authentication, encryption, RBAC, audit log immutability, rate limiting
- **Why**: Not required for take-home; would significantly increase complexity
- **Current**: Basic safety guardrails and redaction
- **Next**: Add Auth0/OIDC, encrypt evidence S3 buckets, WORM log storage

**6. Advanced Error Recovery**
- **What**: Bounded LLM recovery on replay failure, multi-run stability testing
- **Why**: Stretch goals; core error handling is sufficient
- **Current**: Pre-defined error handlers with recovery actions
- **Next**: Add single-step LLM recovery with policy checks, N-run stability scoring

**7. Cross-Tenant Canonicalization**
- **What**: Normalize tenant-specific values into parameterized patterns
- **Why**: Complex; would require ML or sophisticated pattern matching
- **Current**: Manual parameterization during discovery
- **Next**: Build canonicalization service that detects patterns like `/item/12345` → `/item/:id`

### Intentionally Simplified

**1. Single-Process Architecture**
- **Simplification**: No queues, workers, or distributed coordination
- **Trade-off**: Can't scale horizontally, but simpler to develop and test
- **Next**: Add Redis queue + Celery workers for replay scaling

**2. File-Based Evidence Storage**
- **Simplification**: Evidence stored in local filesystem
- **Trade-off**: Not distributed, but simple and sufficient for demo
- **Next**: S3-compatible storage with lifecycle policies

**3. SQLite for Metadata** (not implemented, would be next)
- **Simplification**: Would use SQLite for artifact/evidence metadata
- **Trade-off**: Single-node, but sufficient for many use cases
- **Next**: PostgreSQL for production, SQLite for local dev

**4. Basic Retry Logic**
- **Simplification**: Simple retry with fixed count
- **Trade-off**: No exponential backoff or circuit breaking
- **Next**: Add sophisticated retry with backoff, jitter, circuit breaker

### What I'd Build Next

With more time, my priorities would be:

1. **Agent-Facing API**: FastAPI endpoints so AI agents can discover and invoke capabilities programmatically
2. **Operator Console**: Web-based interface for human operators with live session preview
3. **Artifact Registry**: Database-backed catalog of capabilities with search and versioning
4. **Desktop Surface**: Actual implementation for Windows using UI Automation
5. **Drift Detection**: Automated monitoring of replay success rates with alerting
6. **Production Hardening**: Authentication, encryption, RBAC for real deployment

The current implementation provides a complete, working vertical slice that demonstrates all core requirements while keeping complexity manageable.
