# Workflow Failure Pattern

Demonstrates a resilient AAP workflow pattern that tracks per-host success/failure and uses `set_stats` to route workflow execution based on results.

## Playbooks

### `recovery.yml`
Core workflow node. Uses a `block`/`rescue` pattern to attempt a task on each host and track outcomes. Aggregates successful and failed host lists, then passes them as workflow artifacts via `set_stats` — enabling downstream workflow nodes to target only failed or successful hosts.

### `failure.yml`
Workflow node that runs when hosts have failed. Displays the list of hosts that did not recover, for reporting or alerting purposes.

### `success.yml`
Workflow node that runs when all hosts succeeded.

### `failure_rescue_init.yml`
Initializes the failure/rescue state before the main workflow run.

### `setup.yml`
Sets up prerequisite configuration for the workflow demo.

### `set_stats_test.yml`
Tests the `set_stats` module behavior in isolation.

## Pattern Overview
```
[recovery.yml] → set_stats(successful_nodes, failed_nodes)
     ├── on failure_nodes present → [failure.yml]
     └── on all success → [success.yml]
```

This pattern enables targeted retry or remediation workflows without re-running tasks on already-successful hosts.
