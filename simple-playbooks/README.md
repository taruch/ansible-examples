# Simple Playbooks

Minimal playbooks for basic Ansible operations and debugging.

## Playbooks

### `print_vars.yml`
Prints all variables available in the current play using `debug: var=vars`. Useful for inspecting what variables are in scope — from inventory, facts, extra vars, and group/host vars.
