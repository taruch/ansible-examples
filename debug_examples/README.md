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

---

## show_mounts.yml

Prints all mount points on the target host in a `df -h` style format using gathered facts (`ansible_facts['mounts']`) — no shell commands required.

### Variables

| Variable | Default | Description |
|---|---|---|
| `_hosts` | `localhost` | Target host or group |

### Usage

```bash
ansible-playbook show_mounts.yml -i "<host>," -e "_hosts=<host>"
```

### What it does

- Iterates `ansible_facts['mounts']` with `set_fact` to accumulate one formatted line per mount into a `df_report` list (header row + data rows)
- Prints `df_report` in a **single debug task per host**, so the full table appears as one consolidated block instead of one debug message per mount
- Uses the `human_readable` filter to convert bytes to GB/MB for the Size/Used/Avail columns

Note: facts only populate `mounts` on hosts where the setup module can collect them (Linux/Unix). For Windows, use `ansible_facts['disks']` or run `win_disk_facts`.

---

## network_interfaces_csv.yml

Uses `arista.eos.eos_facts` to gather `ansible_net_interfaces` from Arista EOS devices and produces a CSV report with one row per interface.

### Variables

| Variable | Default | Description |
|---|---|---|
| `_hosts` | `all` | Target host or group (network devices) |
| `report_path` | `/tmp/network_interfaces.csv` | Output CSV file path |

### Usage

```bash
# All devices in inventory
ansible-playbook network_interfaces_csv.yml -i inventory

# Specific group
ansible-playbook network_interfaces_csv.yml -i inventory -e "_hosts=eos_switches"

# Custom output path
ansible-playbook network_interfaces_csv.yml -i inventory -e "report_path=/opt/reports/interfaces.csv"
```

### CSV Columns

| Column | Source | Notes |
|---|---|---|
| `hostname` | inventory hostname | sorted alphabetically |
| `interface` | `ansible_net_interfaces` dict key | sorted per host |
| `ip_address` | `ipv4[].address` | multiple IPs joined with `;` |
| `subnet` | `ipv4[].subnet` | multiple subnets joined with `;` |
| `mac_address` | `macaddress` | |
| `mtu` | `mtu` | |
| `speed_mbps` | `bandwidth` | converted from bps to Mbps |
| `duplex` | `duplex` | |
| `status` | `operstatus` | e.g. `up`, `down` |
| `description` | `description` | interface description if configured |

### How it works

1. **Play 1** runs `arista.eos.eos_facts` with `gather_subset: interfaces` against the target devices
2. **Play 2** runs on `localhost` and renders a Jinja2 CSV template using `hostvars[]` from Play 1
3. The report is written to disk and printed to stdout

Hosts without `ansible_net_interfaces` (e.g. Linux hosts accidentally included) are silently skipped.
