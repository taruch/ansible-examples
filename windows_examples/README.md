# Windows

Playbooks for common Windows administration tasks using WinRM and the `ansible.windows` / `community.windows` collections.

## Basic Playbooks

### `ping.yml`
Tests connectivity to Windows hosts using `win_ping`. Good first step to verify WinRM is configured correctly.

### `create-user.yml`
Creates a local user account (`ansible`) with a specified password on Windows hosts using the `win_user` module.

### `enable-iis.yml`
Enables and configures IIS (Internet Information Services) on Windows Server targets.

### `deploy-site.yml`
Deploys a web application or static site to an IIS-managed Windows host.

### `install-msi.yml`
Installs a Windows application from an MSI package using `win_package`.

### `run-powershell.yml`
Executes a PowerShell script from the Ansible controller on Windows hosts using `ansible.builtin.script`.

### `win_powershell_script_paths.yml`
Comprehensive reference for the different ways to run PowerShell scripts with `ansible.windows.win_powershell`, `ansible.windows.win_shell`, and `ansible.builtin.script`. Tested against Windows Server 2019 Datacenter on AWS EC2 using the `apd-ee-25:latest` execution environment.

| Option | Approach | Result |
|--------|----------|--------|
| 1 | Inline script block | ✅ Pass |
| 2 | Controller file via `script` parameter | ✅ Pass |
| 3 | Controller file via `path` + `remote_src=False` | ❌ Fail — collection bug in EE (`DataLoader` error); use Option 2 |
| 4 | `ansible.builtin.script` (explicit copy) | ✅ Pass |
| 5 | Remote absolute path via `path` + `remote_src=True` | ✅ Pass |
| 6 | Remote relative path via `path` + `chdir` | ❌ Fail — `chdir` does not resolve `path` despite docs saying it should |
| 7 | Remote absolute path with `chdir` (controls execution dir) | ✅ Pass |
| 7b | Relative path via inline `& ".\script.ps1"` + `chdir` | ✅ Pass — correct workaround for relative paths |
| 8 | `win_shell` with absolute path | ✅ Pass |
| — | Structured output capture via `result.output[0]` | ✅ Pass |

**Key findings:**
- `chdir` sets the working directory *during* execution but does **not** help the `path` parameter locate the script — use absolute paths with `path`
- The correct relative path workaround is an inline `script` block using `& ".\script.ps1"` after setting `chdir`
- `win_powershell` uses `result.output`, `result.host_out`, and `result.host_err` — not `stdout_lines` (that is a `win_shell`/`command` attribute)

Run `setup_test_env.yml` first to deploy the required test script to `C:\scripts\report.ps1` on the remote host.

### `map_json.yml`
Demonstrates parsing and mapping JSON data returned from Windows commands or files.

### `test.yml`
General-purpose test playbook for validating Windows host connectivity and module behavior.

### `ad_deploy_primary_dc.yml`
Deploys a new Active Directory forest and promotes a Windows Server to the primary domain controller. Installs the AD DS and DNS Server Windows features, creates the AD forest using `microsoft.ad.domain`, reboots the server, waits for ADWS (port 9389) and LDAP (port 389) to become available, then verifies domain health via PowerShell.

**Survey variables**: `_hosts` (target server), `domain_name` (FQDN, e.g. `example.local`), `domain_netbios_name` (e.g. `EXAMPLE`), `safe_mode_password` (DSRM password)

### `ad_join_domain.yml`
Joins a Windows server to an existing Active Directory domain. Uses `microsoft.ad.membership` to perform the domain join against a specified domain controller, reboots when required, waits for WinRM to recover, then asserts domain membership via WMI.

**Survey variables**: `_hosts` (target server), `domain_controller` (hostname or IP of the DC — required, no default), `domain_name`, `domain_admin_user`, `domain_admin_password`

---

## Advanced Examples

### System Event Response (Alert-Driven Automation)

These playbooks are designed to be triggered by monitoring systems (Nagios, Zabbix, Prometheus, etc.) via AAP webhooks when alerts fire. They provide detailed investigation reports and actionable data for incident response.

#### `system_event_cpu_alert.yml`

**Purpose**: Investigate high CPU usage alerts and generate comprehensive performance reports.

**Use Case**: Your monitoring system detects CPU usage above 80% and triggers this playbook via AAP webhook to gather diagnostic information.

**What It Does**:
- Measures current CPU usage with multi-sample averaging
- Identifies top 10 CPU-consuming processes
- Collects system performance counters (processor time, queue length, context switches)
- Checks for running scheduled tasks
- Verifies Windows Update service status
- Generates JSON report saved to controller
- Sets AAP dashboard statistics for visibility

**Variables**:
| Variable | Default | Description |
|----------|---------|-------------|
| `_hosts` | `all` | Target hosts (typically passed via survey) |
| `cpu_threshold` | `80` | Alert threshold percentage |
| `top_process_count` | `10` | Number of top processes to report |
| `report_dir` | `/tmp/windows_reports` | Controller directory for reports |

**Example Execution**:
```bash
# Via AAP job template with survey
# Survey prompts for: _hosts, cpu_threshold

# Via ansible-playbook
ansible-playbook system_event_cpu_alert.yml \
  -e "cpu_threshold=85" \
  -e "_hosts=windows_prod"
```

**Output**:
- Console: Formatted alert summary with performance data
- File: `/tmp/windows_reports/cpu_alert_<hostname>_<timestamp>.json`
- AAP Stats: `cpu_current`, `top_process`, `alert_severity`

**AAP Integration**:
Configure as a job template with webhook enabled. Your monitoring system calls:
```bash
curl -X POST https://aap-host/api/v2/job_templates/<id>/launch/ \
  -H "Authorization: Bearer <token>" \
  -d '{"extra_vars": {"_hosts": "server01", "cpu_threshold": 90}}'
```

---

#### `system_event_memory_alert.yml`

**Purpose**: Investigate high memory usage alerts with detailed memory consumption analysis.

**Use Case**: Memory utilization exceeds threshold and you need to identify memory leaks, runaway processes, or resource exhaustion.

**What It Does**:
- Calculates total/used/free memory with percentages
- Identifies top 10 memory-consuming processes with private/virtual memory breakdown
- Analyzes page file usage and allocation
- Collects memory performance counters (committed bytes, cache, pool usage, page faults)
- Identifies memory-intensive Windows services
- Provides system hardware information
- Generates comprehensive JSON report

**Variables**:
| Variable | Default | Description |
|----------|---------|-------------|
| `_hosts` | `all` | Target hosts |
| `memory_threshold` | `85` | Alert threshold percentage |
| `top_process_count` | `10` | Number of top processes to report |
| `report_dir` | `/tmp/windows_reports` | Controller directory for reports |

**Example Execution**:
```bash
ansible-playbook system_event_memory_alert.yml \
  -e "memory_threshold=90" \
  -e "_hosts=windows_db_servers"
```

**Output**:
- Console: Memory usage summary, top processes, page file status
- File: `/tmp/windows_reports/memory_alert_<hostname>_<timestamp>.json`
- AAP Stats: `memory_percent_used`, `memory_used_gb`, `top_process_memory_mb`

**Key Metrics Collected**:
- Working Set vs Private Memory vs Virtual Memory (per process)
- Page file allocation and current/peak usage
- Memory pools (paged and non-paged)
- Cache bytes and page faults per second
- Service memory consumption (>50MB only)

---

#### `system_event_disk_alert.yml`

**Purpose**: Investigate disk space alerts and identify storage consumption patterns.

**Use Case**: Disk space drops below threshold and you need to quickly identify what's consuming space and where growth is occurring.

**What It Does**:
- Scans all fixed disk volumes with usage percentages
- Collects disk I/O performance counters (queue length, read/write latency, IOPS)
- Identifies top 10 largest folders on critical drives (>threshold)
- Finds large files (>100MB by default) on critical drives
- Checks Windows log file sizes
- Measures Windows Update cache size
- Generates detailed space consumption report

**Variables**:
| Variable | Default | Description |
|----------|---------|-------------|
| `_hosts` | `all` | Target hosts |
| `disk_threshold` | `85` | Alert threshold percentage |
| `target_drives` | `[]` | Specific drives to check (empty = all) |
| `large_file_size_mb` | `100` | Minimum file size for large file scan |
| `top_folder_count` | `10` | Number of largest folders to report |
| `report_dir` | `/tmp/windows_reports` | Controller directory for reports |

**Example Execution**:
```bash
ansible-playbook system_event_disk_alert.yml \
  -e "disk_threshold=90" \
  -e "large_file_size_mb=500" \
  -e "_hosts=file_servers"
```

**Output**:
- Console: Disk volume summary, largest folders/files, log sizes
- File: `/tmp/windows_reports/disk_alert_<hostname>_<timestamp>.json`
- AAP Stats: `critical_drives_count`, `largest_folder_gb`, `alert_severity`

**Performance Notes**:
- Large file/folder scanning uses `async: 300` with polling to prevent timeouts
- Scans only critical drives (exceeding threshold) to minimize impact
- Recursion depth is managed to balance detail vs performance

---

### PowerShell Script Integration

#### `create_shared_drive.yml`

**Purpose**: Demonstrates how to utilize existing PowerShell scripts with Ansible, passing parameters and capturing structured output.

**Use Case**: Your organization has existing PowerShell automation scripts that you want to integrate into AAP workflows without rewriting them as Ansible modules.

**What It Does**:
- Copies PowerShell script from controller to remote host
- Executes PowerShell script with parameters passed from Ansible variables
- Captures structured JSON output from PowerShell
- Validates share creation and permissions
- Cleans up temporary files
- Reports results to AAP dashboard

**PowerShell Script**: `files/Create-SharedDrive.ps1`

The script:
- Creates a new Windows file share with SMB and NTFS permissions
- Supports Read, Change, and Full Control permission groups
- Can remove and replace existing shares
- Returns structured JSON output for Ansible parsing
- Includes error handling and rollback capabilities

**Variables**:
| Variable | Default | Description |
|----------|---------|-------------|
| `_hosts` | `all` | Target hosts |
| `share_name` | `TeamShare` | SMB share name |
| `share_path` | `C:\Shares\TeamShare` | Local filesystem path |
| `share_description` | `Team collaboration share...` | Share description |
| `read_only_users` | `["Domain Users"]` | Users/groups with Read access |
| `change_users` | `["TeamA", "TeamB"]` | Users/groups with Change access |
| `full_control_users` | `["Administrators", "ShareAdmins"]` | Users/groups with Full Control |

**Example Execution**:
```bash
ansible-playbook create_shared_drive.yml \
  -e "share_name=ProjectX" \
  -e "share_path=C:\\Shares\\ProjectX" \
  -e "change_users=['ProjectX-Editors']" \
  -e "_hosts=file_server01"
```

**Output Structure**:
```json
{
  "success": true,
  "share_name": "TeamShare",
  "share_path": "C:\\Shares\\TeamShare",
  "unc_path": "\\\\SERVER01\\TeamShare",
  "permissions": {
    "read": ["Domain Users"],
    "change": ["TeamA", "TeamB"],
    "full_control": ["Administrators", "ShareAdmins"]
  }
}
```

**Extending the Pattern**:

This playbook demonstrates the general pattern for integrating existing PowerShell scripts:

1. **Copy script to remote host** (or use a centralized script share)
2. **Execute with parameters** using `win_powershell` or `ansible.builtin.script`
3. **Return structured JSON** from PowerShell for easy parsing
4. **Validate results** using assertions
5. **Clean up** temporary files

You can apply this pattern to existing PowerShell scripts for:
- Active Directory user provisioning
- Group Policy management
- IIS site creation and configuration
- SQL Server database operations
- Certificate deployment
- Scheduled task creation

---

### Large-Scale Application Deployment

#### `mass_application_deployment.yml`

**Purpose**: Deploy executable applications to thousands of Windows machines with validation, rollback, and batch processing.

**Use Case**: Deploy a new version of an internal application to 2,500 workstations or servers, ensuring each installation succeeds and can be rolled back if it fails.

**Architecture Features**:
- **Batch Processing**: Uses `serial: 20%` to process hosts in waves, preventing network/service overload
- **Pre-deployment Checks**: Validates disk space and OS version before attempting installation
- **Version Detection**: Skips hosts already running the target version
- **Backup & Rollback**: Automatically backs up existing installation and restores on failure
- **Validation**: Verifies installation via registry, filesystem, and service checks
- **Async Operations**: Install timeout of 10 minutes with polling
- **Retry Logic**: Downloads retry 3 times with 10-second delays
- **Detailed Reporting**: Per-host stats sent to AAP dashboard

**What It Does**:
1. **Pre-checks**: Validates disk space and OS compatibility
2. **Skip Logic**: Exits early if target version already installed
3. **Backup**: Creates timestamped backup of existing installation
4. **Download**: Fetches installer from artifact repository with retries
5. **Verify**: Checksums downloaded file (SHA256)
6. **Install**: Executes silent installation with custom arguments
7. **Validate**: Confirms registry entry, executable existence, and service status
8. **Cleanup**: Removes installer file
9. **Rollback** (on failure): Restores backup if installation fails

**Variables**:
| Variable | Default | Description |
|----------|---------|-------------|
| `_hosts` | `all` | Target hosts |
| `batch_size` | `20%` | Percentage of hosts per batch |
| `app_source_path` | `https://...` | URL to application installer |
| `app_destination` | `C:\Windows\Temp\...` | Local download path |
| `app_install_path` | `C:\Program Files\MyApp` | Installation directory |
| `app_name` | `MyApplication` | Application name for registry lookups |
| `app_version` | `2.5.0` | Target version number |
| `install_arguments` | `/S /D=...` | Silent installer arguments |
| `reboot_required` | `false` | Whether installation requires reboot |
| `max_install_timeout` | `600` | Maximum install time in seconds |
| `validate_installation` | `true` | Enable post-install validation |
| `app_executable` | `MyApp.exe` | Main executable for validation |
| `expected_service_name` | `MyAppService` | Service name (empty if none) |
| `enable_rollback` | `true` | Enable automatic rollback on failure |
| `backup_existing` | `true` | Backup before overwriting |
| `minimum_disk_space_gb` | `2` | Required free space in GB |

**Example Execution with Variable Files**:

The playbook supports loading all variables from external YAML files for easier management and reusability:

```bash
# Deploy Notepad++ using pre-configured variable file
ansible-playbook mass_application_deployment.yml -e @vars/notepadpp_deployment.yml

# Override specific variables from the file
ansible-playbook mass_application_deployment.yml \
  -e @vars/notepadpp_deployment.yml \
  -e "batch_size=10%" \
  -e "_hosts=windows_workstations"
```

**Available Variable Files** (`vars/` directory):
- `myapp_template.yml` - Fully commented template with examples for creating your own deployment configurations
- `notepadpp_deployment.yml` - Working example: Notepad++ 8.9.6.2 deployment (ready to run)

**Example Execution with Inline Variables**:

Deploy to 2,500 machines in batches of 250 (10%):
```bash
ansible-playbook mass_application_deployment.yml \
  -e "app_source_path=https://artifacts.company.com/releases/MyApp_v3.0.exe" \
  -e "app_version=3.0.0" \
  -e "batch_size=10%" \
  -e "_hosts=windows_all"
```

Deploy with custom installer arguments:
```bash
ansible-playbook mass_application_deployment.yml \
  -e "install_arguments='/quiet /norestart INSTALLDIR=\"C:\\Apps\\MyApp\"'" \
  -e "reboot_required=false"
```

**Performance Considerations**:

For deploying to 2,500 machines:
- **Batch Size**: `20%` = 500 machines per batch, 5 batches total
- **Forks**: 50 parallel executions per batch = 10 rounds per batch
- **Estimated Time**: 
  - Download: ~2 minutes per round
  - Install: ~5 minutes per round
  - Total per batch: ~70 minutes
  - Total deployment: ~6 hours for all batches

Tuning recommendations:
- **Faster deployment**: Increase `batch_size` to `50%` and `forks` to 100
- **Safer deployment**: Decrease `batch_size` to `10%` for slower rollout
- **Pre-stage installers**: Copy installer to file share first, then install from `\\fileserver\apps\`
- **Use instance groups**: Assign AAP execution nodes to specific regions/datacenters

**Validation Strategy**:

The playbook validates installation success through multiple checks:

1. **Registry Validation**: Confirms entry in `HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall`
2. **Filesystem Validation**: Verifies executable exists at expected path
3. **Service Validation**: Confirms Windows service is running (if applicable)
4. **Version Validation**: Checks executable file version matches target

All checks must pass for `installation_verified: true`.

**Rollback Mechanism**:

On installation failure:
1. Failed installation is removed from `app_install_path`
2. Timestamped backup is restored from `backup_path`
3. Rollback success/failure is logged to AAP stats
4. Original error is re-raised for AAP to mark job as failed

**Common Installer Argument Patterns**:

| Installer Type | Silent Arguments | Notes |
|----------------|------------------|-------|
| MSI | `/quiet /norestart` | Standard Windows Installer |
| NSIS | `/S` | Nullsoft installer (case-sensitive) |
| Inno Setup | `/VERYSILENT /NORESTART` | Common for open-source apps |
| InstallShield | `/s /v"/qn"` | Enterprise installers |
| Custom EXE | Varies | Check vendor documentation |

---

#### `mass_application_deployment_optimized.yml`

This is an optimized version of the mass deployment playbook that replaces PowerShell-based tasks with native Ansible modules wherever possible for better idempotency, error handling, and maintainability.

**Key Optimizations**:
- Uses `ansible.windows.win_package` with check mode for idempotent install checks
- Uses `ansible.windows.win_stat` instead of PowerShell for file verification
- Uses `ansible.windows.win_copy` with `remote_src: true` for backups
- Uses `ansible.windows.win_file` for directory operations
- Uses `ansible.windows.win_reg_stat` for registry validation
- Uses `ansible.windows.win_service_info` for service status checks
- Uses `community.windows.win_disk_facts` for disk information gathering

See **[MODULE_OPTIMIZATION_GUIDE.md](MODULE_OPTIMIZATION_GUIDE.md)** for detailed comparison of PowerShell vs native Ansible modules and when to use each approach.

---

## Microsoft SQL Server

For SQL Server deployment, backup, and restore playbooks, see the [**windows_mssql_examples**](../windows_mssql_examples/) directory.

---

## Requirements

- WinRM configured on target Windows hosts (HTTP port 5985 or HTTPS port 5986)
- Windows host variables: `ansible_user`, `ansible_password`, `ansible_connection: winrm`
- `ansible.windows`, `community.windows`, and `microsoft.ad` collections
- PowerShell version 5.1 or later on target hosts

Install required collections:
```bash
ansible-galaxy collection install ansible.windows community.windows microsoft.ad
```

---

## Adding to Ansible Automation Platform

You can load these playbooks as job templates in AAP by running the `setup_demo.yml` playbook from the root of the repo:

```bash
export CONTROLLER_PASSWORD=<changeme>
export CONTROLLER_USERNAME=<changeme>
export CONTROLLER_HOST=<changeme>
export CONTROLLER_VERIFY_SSL=false
ansible-navigator run -mstdout setup_demo.yml --eei=quay.io/ansible-product-demos/apd-ee-25:latest \
  --penv=CONTROLLER_USERNAME --penv=CONTROLLER_PASSWORD --penv=CONTROLLER_HOST --penv=CONTROLLER_VERIFY_SSL \
  -e demo=windows_examples
```

This creates:
- **Windows Demo Credential** — Machine credential for WinRM access
- **Windows Inventory** — inventory for targeting Windows hosts
- **WINDOWS / AD / Deploy Primary Domain Controller** — job template with survey
- **WINDOWS / AD / Join Domain** — job template with survey
- **WINDOWS / AD / Full AD Deployment** — workflow that chains DC deployment → domain join

---

## Best Practices

### System Event Response Playbooks
- **Trigger via webhook**: Configure monitoring systems to call AAP webhooks on alert
- **Set appropriate thresholds**: Adjust based on workload patterns (CPU: 80-90%, Memory: 85-95%, Disk: 80-90%)
- **Review reports regularly**: Archive JSON reports and analyze trends
- **Automate remediation**: Chain these investigation playbooks with remediation workflows

### PowerShell Integration
- **Return structured data**: Always use JSON output from PowerShell for easy parsing
- **Include error handling**: PowerShell scripts should catch exceptions and return error objects
- **Use splatting**: Pass parameters as hashtables (`@params`) for readability
- **Clean up**: Remove temporary scripts unless debugging

### Mass Deployment
- **Test in dev first**: Always validate on non-production before scaling
- **Use smaller batches initially**: Start with `batch_size: 5%` for first rollout
- **Monitor AAP capacity**: Watch execution node CPU/memory during large deployments
- **Schedule during maintenance windows**: Large deployments can impact network and endpoints
- **Enable rollback for production**: Only disable for testing environments

---

## Troubleshooting

### Common Issues

**Problem**: "Insufficient disk space" error
- **Solution**: Adjust `minimum_disk_space_gb` or free up space on targets

**Problem**: Validation fails but app is installed
- **Solution**: Check `expected_service_name` and `app_executable` variables match actual installation

**Problem**: Installation times out
- **Solution**: Increase `max_install_timeout` for large applications

**Problem**: Download fails repeatedly
- **Solution**: Verify `app_source_path` is accessible from target hosts, check firewall/proxy

**Problem**: PowerShell script returns "permission denied"
- **Solution**: Verify execution policy allows scripts, consider signing or using `-ExecutionPolicy Bypass`

**Problem**: Batch deployment too slow
- **Solution**: Increase `batch_size` and AAP `forks`, consider pre-staging installers
