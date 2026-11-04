# Incident Enrichment Role

## Description

OS-agnostic role for investigating CPU, memory, and disk alerts. Automatically
detects the operating system (Windows or Linux) via `ansible_os_family` and
runs the matching investigation tasks for the requested `incident_type`. This
replaces the previous `incident_enrichment_cpu`, `incident_enrichment_memory`,
and `incident_enrichment_disk` roles with a single role.

This role only gathers data - it does not set workflow stats itself. The
calling playbook is responsible for publishing `alert_report_json` via
`set_stats` so it can be picked up by a downstream workflow node (e.g.
`servicenow_incident_update.yml`).

Hosts that are neither Windows nor Linux fail fast with a clear error, as do
runs where `incident_type` is missing or not one of `cpu`, `memory`, `disk`.

## Role Variables

Defined in `defaults/main.yml`:

- `incident_type`: **Required** (passed by the caller) - `cpu`, `memory`, or `disk`
- `cpu_threshold`: CPU alert threshold percentage (default: 80)
- `memory_threshold`: Memory alert threshold percentage (default: 85)
- `disk_threshold`: Disk alert threshold percentage (default: 85)
- `top_process_count`: Number of top processes to report for CPU/memory (default: 10)
- `target_drives` / `target_filesystems`: Reserved for scoping disk checks (default: `[]`)
- `large_file_size_mb`: Disk - minimum size to flag a file as "large" (default: 100)
- `top_folder_count` / `top_directory_count`: Disk - how many largest folders/directories to report (default: 10)
- `report_dir`: Output directory on the controller, defaults to `/tmp/{{ incident_type }}_reports`

## Example Usage

### Standalone Playbook

```yaml
---
- name: CPU Investigation Report
  hosts: "{{ _hosts | default('all') }}"
  gather_facts: true

  roles:
    - role: incident_enrichment
      vars:
        incident_type: cpu

  post_tasks:
    - name: Set stats for AAP dashboard and workflow
      ansible.builtin.set_stats:
        data:
          alert_data: "{{ alert_report_json }}"
        per_host: true
        aggregate: false
```

### With Custom Thresholds

```yaml
---
- name: Memory Investigation with Custom Threshold
  hosts: all
  gather_facts: true

  roles:
    - role: incident_enrichment
      vars:
        incident_type: memory
        memory_threshold: 90
        top_process_count: 20
```

### AAP Workflow Integration

The calling playbook publishes `alert_data` (the `alert_report_json` fact
this role builds) via `set_stats`, which can be consumed by the next workflow
node (e.g. ServiceNow incident update). See `incident_enrichment_cpu.yml`,
`incident_enrichment_memory.yml`, `incident_enrichment_disk.yml`, and the
`issue`-driven `incident_enrichment.yml` dispatcher one directory up for
working examples.

## Output Data Structure

`alert_report_json` structure varies by `incident_type` (`alert_type` is
`high_cpu`, `high_memory`, or `high_disk_usage` respectively) - see
`../README.md` for the full contract consumed by `servicenow_incident_update.yml`.

## Linux Data Collected

- **CPU**: usage from `/proc/stat`, top processes, load averages, context
  switches/interrupts, processor info, zombie processes, uptime
- **Memory**: `/proc/meminfo` breakdown, swap, top processes, OOM killer
  history, memory-intensive services, NUMA info
- **Disk**: per-filesystem usage and inode usage, critical filesystems, top
  largest directories/files on critical filesystems, log/cache directory
  sizes, journal size

## Windows Data Collected

- **CPU**: usage from Performance Counters, top processes, performance
  counters, processor info, running scheduled tasks, Windows Update service
  status, uptime
- **Memory**: `Win32_OperatingSystem` memory stats, top processes, page file
  usage, memory performance counters, memory-intensive services
- **Disk**: fixed volume usage, disk performance counters, top largest
  folders/files on critical drives, Windows log/Windows Update cache sizes

## Files

- `tasks/main.yml` - validates `incident_type` and host OS, routes to the
  matching `<incident_type>_<os>.yml` task file
- `tasks/cpu_linux.yml` / `tasks/cpu_windows.yml`
- `tasks/memory_linux.yml` / `tasks/memory_windows.yml`
- `tasks/disk_linux.yml` / `tasks/disk_windows.yml`
- `defaults/main.yml` - default variables
