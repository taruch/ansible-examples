# Debug Examples

A utility playbook for inspecting Ansible variables, inventory sources, and group membership at runtime. Useful for troubleshooting host/group variable resolution and fact sequencing.

## Usage

```bash
ansible-playbook debug.yml -i "<host>," -e "_hosts=<host>"
```

Defaults to `localhost` if `_hosts` is not provided.

## Variables

| Variable | Default | Description |
|---|---|---|
| `_hosts` | `localhost` | Target host or group |
| `try_facts` | `false` | Set to `true` to test sequential fact assignment |
| `clear_facts` | `false` | Set to `true` to clear the fact cache after the run |

## What it does

- **Show all vars** — dumps the full `vars` dictionary for the host
- **Inventory sources** — shows which inventory sources were used for the host
- **Group names** — lists all groups the host belongs to
- **Group variable audit** — loops over each group and prints the variables inherited from it
- **localhost hostvars** — prints all hostvars for `localhost` when `ask_limit_on_launch` is defined there

### Sequential fact testing (`try_facts=true`)

Demonstrates that `set_fact` does **not** evaluate facts sequentially within a single task — `fact_2` and `fact_3` will not resolve based on `fact_1` set in the same task. Use separate `set_fact` tasks for dependent facts.

```bash
ansible-playbook debug.yml -e "try_facts=true"
```

---

## run_until_one_succeeds.yml

Demonstrates the `serial: 1` + `meta: end_play` pattern for running a task across a host group and stopping immediately after the first successful execution.

### How it works

1. `serial: 1` ensures hosts are attempted one at a time
2. `ignore_errors: true` on the task prevents a failure from aborting the play before the next host is tried
3. `meta: end_play` fires as soon as a host succeeds, skipping all remaining hosts cleanly

### Variables

| Variable | Default | Description |
|---|---|---|
| `_hosts` | `localhost` | Target host or group |
| `simulated_failure_hosts` | `[]` | List of hostnames that will simulate a script failure |

### Usage

Quick local demo — two hosts fail, third succeeds:

```bash
ansible-playbook run_until_one_succeeds.yml \
  -i "host1,host2,host3,host4," \
  -e "_hosts=all" \
  -e '{"simulated_failure_hosts": ["host1", "host2"]}'
```

Against a real inventory group:

```bash
ansible-playbook run_until_one_succeeds.yml \
  -i inventory/ \
  -e "_hosts=script_runners"
```

### When to use `meta: end_play` vs `meta: end_host`

| Meta action | Effect |
|-------------|--------|
| `meta: end_play` | Stops the play for ALL remaining hosts — correct for this pattern |
| `meta: end_host` | Removes only the current host; others continue — use when you want every host to attempt regardless |
