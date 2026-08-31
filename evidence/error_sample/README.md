# Error Scenario Replay Evidence

This directory contains evidence from a replay run that hit an error condition.

## Session Details
- **Session ID**: replay_error_20240830_120300
- **Execution Type**: replay
- **Artifact ID**: lookup_member_balance
- **Status**: business_outcome
- **Business Outcome**: not_found
- **Steps Executed**: 3
- **Execution Time**: 10.5 seconds

## Files
- `metadata.json`: Session metadata and final status
- `result.json`: Execution result with error details
- `log.jsonl`: Line-by-line log of execution

## What Happened
The replay was executed with an invalid member ID (99999) that doesn't exist in the system.

## Error Handling Demonstration
1. Step 3 (click lookup) executed successfully
2. Checkpoint failed (results table not visible)
3. Error condition matched: "member not found"
4. System correctly identified this as a **business outcome**, not a failure
5. Execution stopped cleanly with outcome "not_found"

## Key Distinction
This demonstrates the critical distinction between:
- **Failure**: Technical error (element not found, timeout, etc.)
- **Business Outcome**: Expected result (member not found, insufficient funds, etc.)

"Member not found" is a legitimate answer the caller needs to know about, not a crash. The system handles it appropriately by returning the business outcome rather than treating it as a failure.
