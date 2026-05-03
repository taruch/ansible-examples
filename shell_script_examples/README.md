# Shell Script Examples

Demonstrates how to copy and execute shell scripts on remote hosts from an Ansible playbook.

## Playbooks

### `run_script_playbook.yml`
Copies a local shell script to a remote host, executes it, displays the output, then removes the script. Uses a `block`/`always` structure to guarantee cleanup even if the script fails.

## Pattern
```
copy script → execute → display output → cleanup (always)
```

This is the recommended approach when you need to run an existing shell script without converting it to Ansible tasks.
