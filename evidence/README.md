# Evidence Directory

This directory contains evidence from automation runs, demonstrating the end-to-end functionality of the computer-use automation system.

## Structure

```
evidence/
├── discovery_sample/    # Evidence from LLM-driven discovery run
├── replay_sample/       # Evidence from successful deterministic replay
├── error_sample/        # Evidence from replay with error condition
└── README.md            # This file
```

## Sample Contents

Each sample directory contains:
- `metadata.json`: Session metadata (start/end time, status, steps executed)
- `result.json`: Execution result (status, outputs, or error details)
- `log.jsonl`: Structured line-by-line log of all actions and decisions
- `README.md`: Explanation of what the sample demonstrates

## What These Samples Demonstrate

### Discovery Sample
- LLM successfully learned how to accomplish a goal
- Generated a structured, typed capability artifact
- Used robust locator strategies for legacy web app
- Defined checkpoints and error handlers
- See: `discovery_sample/`

### Replay Sample
- Deterministic execution without LLM involvement
- Parameter substitution ({{member_id}} → actual value)
- Checkpoint verification
- Much faster than discovery (no LLM reasoning)
- See: `replay_sample/`

### Error Sample
- Error condition detection and handling
- Distinction between business outcomes and failures
- "Member not found" handled as business outcome, not failure
- Clean error reporting with context
- See: `error_sample/`

## Real Evidence

When you run the system using the CLI commands, real evidence will be generated in this directory structure. The samples above show the expected format and content.

## Sensitive Data Redaction

All evidence files have sensitive data automatically redacted:
- SSNs, credit cards, API keys, passwords
- Emails, account numbers
- Any field with "password", "token", "secret" in the name

This ensures that regulated financial data is never persisted in logs or artifacts.
