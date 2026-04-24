# Multihost Report

Generates an HTML status report across multiple hosts covering security agents, services, and system information, then serves it via Apache httpd.

## Playbooks

### `agents_updated_server.yml`
1. Installs and enables `httpd` on localhost to serve the report.
2. Gathers status of security and monitoring agents across all hosts: Splunk, CrowdStrike, Tenable, NXLog, MDATP (Defender), Pacemaker, and others.
3. Collects system metadata: CPU, RAM, kernel version, firmware version.
4. Renders an HTML report with per-host status tables using a Jinja2 template.
5. Writes the rendered report to the httpd document root for browser access.

### `ip_address_report.yml`

Gathers network facts from each host and generates a CSV report on the Ansible controller.

1. Collects `ansible_interfaces` and per-interface IPv4 facts from all target hosts.
2. Loops through the template `ip_address_report.csv.j2` to produce one CSV row per interface per host that has an IPv4 address assigned.
3. Writes the CSV to the controller and prints its contents.

**CSV columns:** `hostname`, `interface`, `ip_address`, `netmask`, `mac_address`

**Variables:**

| Variable | Default | Description |
|---|---|---|
| `_hosts` | `all` | Target host or group |
| `report_path` | `/tmp/ip_address_report.csv` | Output path on the controller |

**Usage:**
```bash
ansible-playbook ip_address_report.yml -i <inventory>
ansible-playbook ip_address_report.yml -i <inventory> \
  -e "_hosts=webservers" \
  -e "report_path=/tmp/webservers_ips.csv"
```

## Requirements
- `httpd` installable on the report server (localhost) — required for `agents_updated_server.yml` only
- SSH access to all monitored hosts
- Hosts grouped appropriately in inventory
