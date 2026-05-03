# Windows

Playbooks for common Windows administration tasks using WinRM and the `ansible.windows` / `community.windows` collections.

## Playbooks

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

## Requirements
- WinRM configured on target Windows hosts (HTTP port 5985 or HTTPS port 5986)
- Windows host variables: `ansible_user`, `ansible_password`, `ansible_connection: winrm`
- `ansible.windows`, `community.windows`, and `microsoft.ad` collections
- `secrets.yml` present in the playbook directory (see `secrets.yml` for variable structure)

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
