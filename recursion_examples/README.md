# Recursion Examples

Demonstrates recursive task execution patterns in Ansible using `include_tasks` with looping.

## Playbooks

### `example1_recursion.yml`
Entry point for the first recursion example. Calls `example1_recurse_task.yml` to recursively process items in a list, re-including the task file until the list is exhausted.

### `example1_recurse_task.yml`
The recursive task file for example 1. Processes the current item and re-includes itself for the next iteration.

### `example2_recursion.yml`
Entry point for the second recursion example, demonstrating a variation of the recursive pattern.

### `example2_recurse_task.yml`
The recursive task file for example 2.

## Notes
Ansible does not natively support recursion, so these examples use `include_tasks` (dynamic inclusion) rather than `import_tasks` (static). Be mindful of recursion depth to avoid stack overflows on large datasets.
