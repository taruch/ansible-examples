# Incident Enrichment Host Role

## Description

General-purpose, OS-agnostic incident enrichment role for Windows and Linux
hosts only. Automatically detects the host type via `ansible_os_family` /
`ansible_system` and runs the matching investigation tasks. Unlike the
single-metric roles (`incident_enrichment_cpu`, `_memory`, `_disk`) or the
service-specific `apache_troubleshoot.yml`/`tomcat_troubleshoot.yml`
playbooks, this role gathers a broad snapshot intended to answer "what's
wrong with this host" in general:

- Services that have failed / stopped unexpectedly
- Filesystems that are full (or close to it)
- Recent error-level log entries

This role is read-only - it does not restart services, clear logs, or
otherwise change anything on the target host. Hosts that are neither Windows
nor Linux (e.g. network devices, ESXi) fail fast with a clear error.

## Role Variables

Defined in `defaults/main.yml`:

- `disk_threshold_percent`: filesystems at or above this percent used are
  flagged as "full" (default: 90)
- `log_lines`: number of recent log entries to inspect (default: 200)
- `log_priority`: Linux only - minimum `journalctl` priority level to treat
  as an error (default: `err`)

## Example Usage

### Standalone Playbook

```yaml
---
- name: Host Health Investigation
  hosts: "{{ _hosts | default('') }}"
  gather_facts: true

  roles:
    - incident_enrichment_host
```

### With Custom Thresholds

```yaml
---
- name: Host Health Investigation
  hosts: "{{ _hosts | default('') }}"
  gather_facts: true

  roles:
    - role: incident_enrichment_host
      vars:
        disk_threshold_percent: 85
        log_lines: 500
```

### AAP Workflow Integration

This role sets `host_diagnostics` via `set_stats`, which can be consumed by
a downstream workflow node (e.g. an AI triage prompt, or a ServiceNow
incident update like `servicenow_add_enrichment_note.yml`).

## Output Data Structure

```json
{
  "host_diagnostics": {
    "alert_type": "host_health",
    "host": "node1",
    "timestamp": "2026-10-26T12:00:00Z",
    "system_info": { "...": "..." },
    "failed_services": ["httpd.service"],
    "failed_service_details": { "httpd.service": ["...systemctl status output..."] },
    "disk_volumes": [{ "filesystem": "/dev/xvda4", "percent_used": 78, "mount_point": "/" }],
    "full_filesystems": [{ "filesystem": "/dev/xvda1", "percent_used": 97, "mount_point": "/var" }],
    "log_errors_recent": ["...recent error log lines..."],
    "issues_detected": true
  }
}
```

`issues_detected` is `true` if any failed services, full filesystems, or
recent error log entries were found - useful for gating downstream actions
(e.g. only post a ServiceNow note when there's actually something to report).

## Linux Data Collected

- Failed services (`systemctl list-units --state=failed`) plus detailed
  `systemctl status` output for each one
- Disk usage per mounted filesystem, with full filesystems flagged
- Recent `journalctl` entries at `err` priority or higher

## Windows Data Collected

- Services with `StartMode=Auto` that are not currently `Running`
- Recent Service Control Manager failure events
- Disk usage per fixed drive (`DriveType=3`), with full drives flagged
- Recent error-level (`Level=2`) entries from the System and Application
  event logs

## Files

- `tasks/main.yml` - host type detection, fails fast on unsupported hosts
- `tasks/linux.yml` - Linux-specific investigation tasks
- `tasks/windows.yml` - Windows-specific investigation tasks
- `defaults/main.yml` - default variables
