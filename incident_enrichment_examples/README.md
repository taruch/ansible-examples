# Incident Enrichment Examples

This directory contains OS-agnostic playbooks for investigating system alerts and enriching ServiceNow incidents with detailed diagnostic data.

## Overview

These playbooks are designed to work in AAP workflows:
1. **Investigation playbook** runs on the target system, gathers diagnostics, outputs data via `set_stats`
2. **ServiceNow update playbook** receives data from previous node and updates incident work notes

## Playbooks

### Investigation Playbooks (OS-Agnostic)

- **`incident_enrichment.yml`** - Main playbook that routes to the `incident_enrichment` role based on the `issue` parameter (`cpu`, `memory`, or `storage`) (Windows & Linux)
- **`incident_enrichment_cpu.yml`** / **`incident_enrichment_memory.yml`** / **`incident_enrichment_disk.yml`** - Single-metric wrappers around the same role, for AAP job templates dedicated to one metric (Windows & Linux)

### ServiceNow Integration

- **`servicenow_incident_update.yml`** - Updates ServiceNow incidents with alert data

### Legacy Playbooks (Deprecated)

The following OS-specific playbooks are deprecated. Use the OS-agnostic versions above:
- `linux_event_cpu_alert.yml`
- `linux_event_memory_alert.yml`
- `linux_event_disk_alert.yml`
- `windows_event_cpu_alert.yml`
- `windows_event_memory_alert.yml`
- `windows_event_disk_alert.yml`

## Roles

The investigation playbooks use a single role from `roles/`:

- **`incident_enrichment`** - CPU, memory, and disk investigation role. The
  caller selects which via the `incident_type` variable (`cpu`, `memory`, or
  `disk`).

The role contains:
- `tasks/main.yml` - validates `incident_type` and host OS, then routes to
  the matching task file
- `tasks/cpu_linux.yml` / `tasks/cpu_windows.yml`
- `tasks/memory_linux.yml` / `tasks/memory_windows.yml`
- `tasks/disk_linux.yml` / `tasks/disk_windows.yml`
- `defaults/main.yml` - default variables

Note: The role focuses on data gathering only. Every calling playbook
(`incident_enrichment.yml`, and the three per-metric wrappers below) handles
`set_stats` itself to pass `alert_data` to the next workflow node.

There is also a separate **`incident_enrichment_host`** role (general host
health - failed services, full filesystems, recent error logs) used by
`incident_enrichment_host.yml`. It is not part of the CPU/memory/disk
consolidation above.

## Usage

### Option 1: AAP Workflow (Recommended)

Create a workflow template with two nodes:

**Node 1: Investigation**
- Job Template: "Incident Enrichment"
- Playbook: `incident_enrichment.yml`
- Extra Vars:
  ```yaml
  issue: cpu  # or 'memory' or 'storage'
  _hosts: <target_host>
  ```

**Node 2: ServiceNow Update**
- Job Template: "ServiceNow Incident Update"
- Playbook: `servicenow_incident_update.yml`
- Extra Vars:
  ```yaml
  incident_number: INC0010001
  # alert_data is automatically passed from Node 1 via workflow artifacts
  ```
- Credentials: ServiceNow credential (provides SN_HOST, SN_USERNAME, SN_PASSWORD)

### Option 2: Standalone

Run investigation only (no ServiceNow update):

```bash
ansible-playbook incident_enrichment.yml -e "issue=cpu _hosts=server01"
```

### Option 3: Command Line with ServiceNow

```bash
# Step 1: Run investigation
ansible-playbook incident_enrichment.yml -e "issue=cpu _hosts=server01"

# Step 2: Use AAP workflow for automatic data passing to ServiceNow
# (set_stats data is only available in AAP workflows via workflow_job.artifacts)
```

## Variables

### Investigation Playbook Variables

- `issue`: Alert type - **Required** (via `incident_enrichment.yml`) - must be `cpu`, `memory`, or `storage`
- `incident_type`: Alert type - **Required** (via the role directly, or the per-metric wrappers set this for you) - must be `cpu`, `memory`, or `disk`
- `_hosts`: Target host or group (default: 'all')
- `cpu_threshold`: CPU alert threshold % (default: 80)
- `memory_threshold`: Memory alert threshold % (default: 85)
- `disk_threshold`: Disk alert threshold % (default: 85)
- `top_process_count`: Number of top processes to report (default: 10)
- `report_dir`: Output directory on controller (default: /tmp/{{ incident_type }}_reports)

### ServiceNow Playbook Variables

- `incident_number`: ServiceNow incident number (e.g., INC0010001) - **Required**
- `alert_data`: JSON from previous workflow node (automatically passed via `workflow_job.artifacts`) - **Required**
- `SN_HOST`: ServiceNow instance URL (from AAP credential) - **Required**
- `SN_USERNAME`: ServiceNow username (from AAP credential) - **Required**
- `SN_PASSWORD`: ServiceNow password (from AAP credential) - **Required**

## Workflow Data Flow

Investigation playbooks use `set_stats` to pass data to the next workflow node:

```
Investigation Node                ServiceNow Node
─────────────────                ───────────────
gather diagnostics
  ↓
build JSON report
  ↓
set_stats:
  alert_data: {...}  ────────→   receives alert_data
                                  ↓
                               parse JSON
                                  ↓
                               build work_notes
                                  ↓
                               update incident
```

## Alert Data Structure

Each investigation playbook outputs the following via `set_stats`:

```json
{
  "alert_type": "high_cpu|high_memory|high_disk_usage",
  "host": "hostname",
  "timestamp": "2026-07-06T12:00:00Z",
  "<metric>_metrics": { ... },
  "system_info": { ... },
  "top_processes": [ ... ],
  ...
}
```

The `alert_data` JSON structure varies by alert type and is consumed by the ServiceNow playbook to generate appropriate work notes.

## Examples

### Example 1: CPU Alert Workflow

AAP Workflow Template: "Incident Enrichment Workflow"

Node 1 (Incident Enrichment) Extra Vars:
```yaml
issue: cpu
_hosts: "webserver01"
cpu_threshold: 90
```

Node 2 (ServiceNow Update) Extra Vars:
```yaml
incident_number: "INC0010123"
# alert_data automatically passed from Node 1
# SN_HOST, SN_USERNAME, SN_PASSWORD provided via AAP ServiceNow credential
```

### Example 2: Memory Alert with Custom Threshold

```bash
ansible-playbook incident_enrichment.yml \
  -e "issue=memory" \
  -e "_hosts=dbserver01" \
  -e "memory_threshold=90" \
  -e "top_process_count=20"
```

## ServiceNow Work Notes

The ServiceNow playbook generates OS-specific work notes based on `alert_type`:

- **high_cpu**: CPU metrics, processor info, top processes, performance counters (Windows & Linux)
- **high_memory**: Memory metrics, swap usage, top processes, OOM killer history (separate templates for Windows & Linux)
- **high_disk_usage**: Disk volumes, critical drives, large files/folders, log sizes (Windows & Linux)

## OS Detection

Roles use `ansible_os_family` to detect the operating system:

- `Windows` → runs `tasks/windows.yml`
- `RedHat`, `Debian`, `Suse` → runs `tasks/linux.yml`
- Other → runs `tasks/linux.yml` (fallback)

## Requirements

### Collections

- `ansible.windows` (for Windows tasks)
- `servicenow.itsm` (for ServiceNow integration)

### Credentials

- SSH credential for Linux hosts
- WinRM credential for Windows hosts
- ServiceNow credential (username/password)
