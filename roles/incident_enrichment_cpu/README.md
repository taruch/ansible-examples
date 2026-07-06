# Incident Enrichment CPU Role

## Description

OS-agnostic role for investigating high CPU alerts. Automatically detects the operating system (Windows or Linux) and runs the appropriate investigation tasks.

## Features

- **Cross-platform**: Works on both Windows and Linux systems
- **Automatic OS detection**: Uses `ansible_os_family` to run OS-specific tasks
- **Workflow integration**: Outputs data via `set_stats` for AAP workflow nodes
- **Comprehensive metrics**: CPU usage, top processes, system info, performance counters

## Role Variables

Defined in `defaults/main.yml`:

- `cpu_threshold`: Alert threshold percentage (default: 80)
- `top_process_count`: Number of top processes to report (default: 10)
- `report_dir`: Output directory on controller (default: /tmp/cpu_reports)

## Example Usage

### Standalone Playbook

```yaml
---
- name: CPU Investigation Report
  hosts: "{{ _hosts | default('all') }}"
  gather_facts: true

  roles:
    - incident_enrichment_cpu
```

### With Custom Variables

```yaml
---
- name: CPU Investigation with Custom Threshold
  hosts: all
  gather_facts: true

  roles:
    - role: incident_enrichment_cpu
      vars:
        cpu_threshold: 90
        top_process_count: 20
```

### AAP Workflow Integration

This role outputs `alert_data` via `set_stats` which can be consumed by the next workflow node (e.g., ServiceNow incident update):

**Workflow Node 1**: Run `incident_enrichment_cpu.yml`
**Workflow Node 2**: Run `servicenow_incident_update.yml` with `alert_data` from previous node

## Output Data Structure

The role sets the following stats for AAP workflows:

```json
{
  "cpu_current": "85.2",
  "cpu_threshold": "80",
  "top_process": "python3",
  "top_process_cpu": "45.3",
  "alert_severity": "CRITICAL",
  "hostname": "server01",
  "uptime_hours": "120.5",
  "alert_data": "{ ... full JSON report ... }"
}
```

## Linux Data Collected

- CPU usage from `/proc/stat`
- Top CPU-consuming processes
- Load averages (1min, 5min, 15min)
- Context switches and interrupts
- Processor information (architecture, cores, sockets)
- Zombie processes
- System uptime

## Windows Data Collected

- CPU usage from Performance Counters
- Top CPU-consuming processes
- Performance counters (% Privileged Time, % User Time, Queue Length, Context Switches)
- Processor information (cores, logical processors)
- Running scheduled tasks
- Windows Update service status
- System uptime

## Files

- `tasks/main.yml` - OS detection and set_stats
- `tasks/linux.yml` - Linux-specific investigation tasks
- `tasks/windows.yml` - Windows-specific investigation tasks
- `defaults/main.yml` - Default variables
