# Shell Script Examples

Demonstrates how to run an existing bash script from an Ansible playbook,
rather than reimplementing its logic in Ansible tasks. Two approaches are
shown; pick whichever fits the script you're wrapping.

## Playbooks

### `run_script_playbook.yml`
Explicit `copy` → `shell` → cleanup pattern:
```
copy script → execute → display output → cleanup (always)
```
Copies `files/my_script.sh` to the remote host, runs it with
`ansible.builtin.shell`, displays stdout, then removes the script in an
`always` block so it's cleaned up even if the script fails. Good when you
want full control over where the script lands and need a guaranteed
cleanup step.

Runs against `hosts: all` and treats any successful exit as `changed`.

### `run_script_module_playbook.yml`
Single-task `ansible.builtin.script` pattern. The module copies the script
to the remote host, executes it, and removes it automatically — no
explicit `copy`/`cleanup` tasks needed. Wraps `files/cleanup_old_logs.sh`,
a stand-in for a pre-existing script a team already runs manually, and
layers on a few practices worth copying into real wrappers:

- **Arguments**: passed via `cmd`, not hardcoded into the script
- **Real idempotency signal**: `changed_when` is derived from the script's
  own `SUMMARY files_removed=X errors=Y` output line, instead of assuming
  "exit 0 means nothing happened"
- **Exit-code-aware failure handling**: `failed_when` only fails the play
  on genuine errors (bad args, missing directory); a partial failure
  (some files couldn't be removed) is surfaced as a warning, not a
  playbook failure
- **Fail-safe targeting**: `hosts: "{{ target_hosts | default('') }}"` —
  the play matches zero hosts (and errors/no-ops) if `target_hosts` isn't
  supplied, instead of silently defaulting to `all`

| Exit code | Meaning |
|-----------|---------|
| `0` | Success, directory scanned |
| `1` | Invalid arguments |
| `2` | Target directory does not exist |
| `3` | Success, but one or more files could not be removed |

## Choosing an approach
| | `run_script_playbook.yml` | `run_script_module_playbook.yml` |
|---|---|---|
| Module(s) | `copy` + `shell` + `file` (cleanup) | `script` (handles copy/run/cleanup) |
| Boilerplate | More explicit, more control | Less boilerplate |
| `changed_when` | Always `changed` on success | Parsed from script output |
| Check mode | Supported (each task runs independently) | Not supported — `script` tasks are skipped under `--check` |
| Use when | You need extra steps around the script (e.g. custom destination, pre/post tasks) | You just need to run the script and capture its result |

## Required Variables (`run_script_module_playbook.yml`)
| Variable | Description |
|----------|-------------|
| `target_hosts` | Inventory group or host pattern to target. Required — the play matches no hosts if omitted. |
| `cleanup_target_dir` | Directory to clean up. Defaults to `/var/log/myapp`. |
| `cleanup_max_age_days` | Delete files older than this many days. Defaults to `30`. |

## Running

```bash
# copy/shell/cleanup pattern
ansible-playbook run_script_playbook.yml

# script module pattern
ansible-playbook run_script_module_playbook.yml \
  -e target_hosts=webservers \
  -e cleanup_target_dir=/var/log/myapp \
  -e cleanup_max_age_days=14
```

As an AAP Job Template, add a survey exposing `target_hosts`,
`cleanup_target_dir`, and `cleanup_max_age_days` as extra vars for
`run_script_module_playbook.yml`.

## Notes
- If the script is already installed on managed nodes (not pushed from the
  control node), skip `copy`/`script` entirely and just call it directly:
  `ansible.builtin.command: /path/to/script.sh arg1 arg2`.
- Avoid `ansible.builtin.shell` unless the script actually needs shell
  features (pipes, globbing, env expansion) at the invocation level —
  `script`/`command` are safer since they don't pass arguments through a
  shell.
