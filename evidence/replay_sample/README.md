# Replay Run Evidence

This directory contains evidence from a successful deterministic replay run.

## Session Details
- **Session ID**: replay_lookup_member_20240830_120200
- **Execution Type**: replay
- **Artifact ID**: lookup_member_balance
- **Status**: success
- **Steps Executed**: 5
- **Execution Time**: 15.2 seconds

## Files
- `metadata.json`: Session metadata and final status
- `result.json`: Execution result with outputs
- `log.jsonl`: Line-by-line log of execution

## Key Outputs
- **Balance**: 5432.10

## What This Demonstrates
- Deterministic replay without LLM involvement
- Parameter substitution (member_id: 12345)
- Checkpoint verification passed
- Successful execution of all 5 steps
- Much faster than discovery (15s vs 90s) because no LLM reasoning needed
