# Incident Enrichment Examples

This directory contains OS-agnostic playbooks for investigating system alerts and enriching ServiceNow incidents with detailed diagnostic data.

## Overview

These playbooks are designed to work in AAP workflows:
1. **Investigation playbook** runs on the target system, gathers diagnostics, outputs data via `set_stats`
2. **ServiceNow update playbook** receives data from previous node and updates incident work notes

## Playbooks

### Investigation Playbooks (OS-Agnostic)

All investigation playbooks use roles that automatically detect the OS and run appropriate tasks:

- **`incident_enrichment_cpu.yml`** - CPU investigation (Windows & Linux)
- **`incident_enrichment_memory.yml`** - Memory investigation (Windows & Linux)
- **`incident_enrichment_disk.yml`** - Disk investigation (Windows & Linux)

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

The investigation playbooks use these roles from `../roles/`:

- **`incident_enrichment_cpu`** - CPU investigation role
- **`incident_enrichment_memory`** - Memory investigation role
- **`incident_enrichment_disk`** - Disk investigation role

Each role contains:
- `tasks/linux.yml` - Linux-specific tasks
- `tasks/windows.yml` - Windows-specific tasks
- `tasks/main.yml` - OS detection and set_stats
- `defaults/main.yml` - Default variables

## Usage

### Option 1: AAP Workflow (Recommended)

Create a workflow template with two nodes:

**Node 1: Investigation**
- Job Template: "Incident Enrichment - CPU" (or Memory/Disk)
- Playbook: `incident_enrichment_cpu.yml`
- Extra Vars: `_hosts: <target_host>`

**Node 2: ServiceNow Update**
- Job Template: "ServiceNow Incident Update"
- Playbook: `servicenow_incident_update.yml`
- Extra Vars (from Node 1): `alert_data`
- Additional Extra Vars: `incident_number: INC0010001`

### Option 2: Standalone

Run investigation only (no ServiceNow update):

```bash
ansible-playbook incident_enrichment_cpu.yml -e "_hosts=server01"
```

### Option 3: Command Line with ServiceNow

```bash
# Step 1: Run investigation and save stats
ansible-playbook incident_enrichment_cpu.yml -e "_hosts=server01" > /tmp/output.txt

# Step 2: Extract alert_data and update ServiceNow
# (Use AAP workflow for easier data passing)
```

## Variables

### Common Variables (Investigation Playbooks)

- `_hosts`: Target host or group (default: 'all')
- `cpu_threshold`: CPU alert threshold % (default: 80)
- `memory_threshold`: Memory alert threshold % (default: 85)
- `alert_threshold`: Disk alert threshold % (default: 85)
- `top_process_count`: Number of top processes to report (default: 10)
- `report_dir`: Output directory on controller (default: /tmp/*_reports)

### ServiceNow Variables

- `incident_number`: ServiceNow incident number (e.g., INC0010001) - **Required**
- `alert_data`: JSON from previous workflow node - **Required**
- `servicenow_host`: ServiceNow instance URL - **Required**
- `servicenow_username`: ServiceNow username (default: admin)
- `vault_servicenow_password`: ServiceNow password (use AAP credential) - **Required**

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

AAP Workflow Template: "Incident Enrichment - CPU Alert"

Node 1 Job Template Extra Vars:
```yaml
_hosts: "webserver01"
cpu_threshold: 90
```

Node 2 Job Template Extra Vars:
```yaml
incident_number: "INC0010123"
servicenow_host: "https://dev12345.service-now.com"
# vault_servicenow_password provided via AAP credential
```

### Example 2: Memory Alert with Custom Threshold

```yaml
- hosts: localhost
  tasks:
    - name: Run memory investigation
      ansible.builtin.import_playbook: incident_enrichment_memory.yml
      vars:
        _hosts: "dbserver01"
        memory_threshold: 90
        top_process_count: 20
```

## ServiceNow Work Notes

The ServiceNow playbook generates work notes conditionally based on `alert_type`:

- **high_cpu**: CPU metrics, processor info, top processes, performance counters
- **high_memory**: Memory metrics, swap usage, top processes, OOM killer history
- **high_disk_usage**: Disk volumes, critical drives, large files/folders, log sizes

## OS Detection

Roles use `ansible_os_family` to detect the operating system:

- `Windows` → runs `tasks/windows.yml`
- `RedHat`, `Debian`, `Suse` → runs `tasks/linux.yml`
- Other → runs `tasks/linux.yml` (fallback)

## Requirements

### Collections

- `ansible.windows` (for Windows tasks)
- `servicenow.servicenow` (for ServiceNow integration)

### Credentials

- SSH credential for Linux hosts
- WinRM credential for Windows hosts
- ServiceNow credential (username/password)
