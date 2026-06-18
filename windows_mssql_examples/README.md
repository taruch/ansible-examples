# Microsoft SQL Server Automation for Windows

Ansible playbooks for deploying, managing, backing up, and restoring Microsoft SQL Server on Windows Server.

## Overview

This directory contains comprehensive automation for SQL Server lifecycle management:

- **Deploy** - Automated download and installation of SQL Server from Microsoft
- **Create** - Create databases with sample data
- **Backup** - Flexible backup solutions (native SQL Server or Cohesity DataProtect)
- **Restore** - Restore databases from backup files
- **AAP Integration** - Ready-to-use Ansible Automation Platform setup

## Quick Start

See [README_AAP.md](README_AAP.md) for Ansible Automation Platform integration.

## Playbooks

### `deploy_mssql.yml` ⭐ PRIMARY

**Fully automated SQL Server 2022 deployment** - downloads and installs from Microsoft with zero manual steps.

**What it does**:
1. Downloads SQL Server bootstrap installer from Microsoft CDN
2. Downloads SQL Server 2022 Developer Edition ISO automatically
3. Installs SQL Server via scheduled task (bypasses WinRM limitations)
4. Configures TCP/IP, firewall rules, and basic security

**Prerequisites**: 
- Windows Server 2016+ with WinRM configured
- At least 2GB RAM on target server
- Internet connectivity from Windows host
- .NET Framework 4.5+ (playbook auto-installs if missing)

**Required variables**: 
- `mssql_sa_password` - SA password (pass via `-e` or secrets.yml)

**Optional variables**: 
- `sql_version` - SQL Server version (default: `2022`)
- `mssql_instance_name` (default: `MSSQLSERVER`)
- `mssql_tcp_port` (default: `1433`)
- `mssql_max_memory_mb` (default: `4096`)
- `mssql_data_dir` (default: `C:\SQLData`)
- `mssql_log_dir` (default: `C:\SQLLogs`)

**Examples**:
```bash
# Basic installation - downloads SQL Server automatically
ansible-navigator run deploy_mssql.yml -i hosts --eei=quay.io/truch/microsoft:3.3 \
  -mstdout -e mssql_sa_password='SecurePassword123!'

# Custom configuration
ansible-navigator run deploy_mssql.yml -i hosts --eei=quay.io/truch/microsoft:3.3 \
  -mstdout -e mssql_sa_password='SecurePassword123!' \
  -e mssql_max_memory_mb=8192 \
  -e mssql_data_dir='D:\SQLData'
```

---

### `deploy_mssql_from_iso.yml` (Alternative)

**For offline/air-gapped environments** - uses pre-downloaded ISO file instead of automatic download.

**Prerequisites**: 
- Download SQL Server ISO from Microsoft beforehand
- Place ISO in `C:\Users\Administrator\Downloads\` on Windows host

**Use this if**: You're in an air-gapped environment or have compliance requirements for offline installation

---

### `create_demo_database.yml`

Downloads SQL Server ISO to the Windows host's Downloads directory from a specified URL.

**Features**:
- Downloads from corporate mirror, S3, Azure blob, or network share
- Skips download if ISO already exists
- Validates downloaded ISO by mounting and checking for setup.exe
- Configurable timeout for large downloads (default 1 hour)

**Key variables**:
- `_mssql_iso_download_url` (required) - URL to download ISO from
- `_mssql_iso_filename` (default: `SQLServer.iso`)
- `_download_timeout` (default: `3600`)
- `_force_download` (default: `false`)

**Examples**:
```bash
# Download from corporate mirror
ansible-navigator run -m stdout download_mssql_iso.yml -i hosts --eei=quay.io/truch/microsoft:3.2 \
  -e _mssql_iso_download_url='https://mirror.example.com/SQLServer2022.iso'

# Custom filename
ansible-navigator run -m stdout download_mssql_iso.yml -i hosts --eei=quay.io/truch/microsoft:3.2 \
  -e _mssql_iso_download_url='https://...' \
  -e _mssql_iso_filename='SQLServer2022-x64-ENU.iso'
```

---

### `backup_mssql.yml`

Flexible backup solution for SQL Server databases with support for both **Cohesity DataProtect** and **native SQL Server backups**.

**Features**:
- Dual backup methods: Cohesity or native SQL Server
- Backup all databases or specific ones
- Multiple backup types: full, differential, transaction log
- Automatic cleanup with configurable retention
- Backup verification with checksum
- Built-in compression support

**Key variables**:
- `_backup_method` (default: `native`) - `native` or `cohesity`
- `_mssql_login_password` (required) - SA password
- `_mssql_database` (default: `all`) - Specific database or "all"
- `_backup_type` (default: `full`) - `full`, `diff`, or `log`
- `_backup_path` (default: `C:\SQLBackups`)
- `_backup_retention_days` (default: `7`)
- `_backup_compression` (default: `true`)
- `_backup_checksum` (default: `true`)
- `_backup_verify` (default: `true`)

**Examples**:
```bash
# Full backup of all databases
ansible-navigator run -m stdout backup_mssql.yml -i hosts --eei=quay.io/truch/microsoft:3.2 \
  -e _mssql_login_password='YourPassword'

# Differential backup of specific database
ansible-navigator run -m stdout backup_mssql.yml -i hosts --eei=quay.io/truch/microsoft:3.2 \
  -e _backup_type=diff \
  -e _mssql_database=ansible \
  -e _mssql_login_password='YourPassword'

# Transaction log backup
ansible-navigator run -m stdout backup_mssql.yml -i hosts --eei=quay.io/truch/microsoft:3.2 \
  -e _backup_type=log \
  -e _mssql_login_password='YourPassword'

# Cohesity backup
ansible-navigator run -m stdout backup_mssql.yml -i hosts --eei=quay.io/truch/microsoft:3.2 \
  -e _backup_method=cohesity \
  -e _cohesity_cluster=cohesity.example.com \
  -e _cohesity_username=admin \
  -e _cohesity_password='CohesityPass' \
  -e _mssql_login_password='SqlPass'
```


---

### `restore_mssql.yml`

Restore SQL Server databases from backup files with comprehensive validation and safety checks.

**Features**:
- Reads backup file header to show contents
- Lists all data/log files in backup
- Protects against accidental overwrites
- Supports restore to different database name
- Custom data/log file paths
- REPLACE, NORECOVERY, RECOVERY modes
- Verifies restore completion

**Key variables**:
- `_backup_file` (required) - Path to .bak file
- `_mssql_login_password` (required) - SA password
- `_database_name` - Restore to different name (optional)
- `_restore_mode` (default: `replace`) - `replace`, `norecovery`, `recovery`
- `_force` (default: `false`) - Force overwrite existing database
- `_data_path` - Custom data file location (optional)
- `_log_path` - Custom log file location (optional)

**Examples**:
```bash
# Basic restore (replace existing database)
ansible-navigator run -m stdout restore_mssql.yml -i hosts --eei=quay.io/truch/microsoft:3.2 \
  -e _backup_file='C:\SQLBackups\ansible_full_20260617T220843.bak' \
  -e _mssql_login_password='YourPassword' \
  -e _force=true

# Restore to different database name
ansible-navigator run -m stdout restore_mssql.yml -i hosts --eei=quay.io/truch/microsoft:3.2 \
  -e _backup_file='C:\SQLBackups\ansible_full_20260617T220843.bak' \
  -e _database_name='ansible_restored' \
  -e _mssql_login_password='YourPassword'

# Restore with NORECOVERY (for log chain)
ansible-navigator run -m stdout restore_mssql.yml -i hosts --eei=quay.io/truch/microsoft:3.2 \
  -e _backup_file='C:\SQLBackups\ansible_full_20260617T220843.bak' \
  -e _restore_mode=norecovery \
  -e _mssql_login_password='YourPassword'
```

---

### `create_demo_database.yml`

Creates a demo database named "ansible" with sample data for testing backups and restores.

**Creates**:
- Database: `ansible`
- Tables: `Users`, `Products`, `Orders`
- Sample data: 10 users, 15 products, 15 orders
- View: `vw_OrderSummary`

**Example**:
```bash
ansible-navigator run -m stdout create_demo_database.yml -i hosts --eei=quay.io/truch/microsoft:3.2 \
  -e _mssql_login_password='YourPassword'
```

---

### `diagnose_sql_install.yml`

Diagnostic playbook to troubleshoot SQL Server installation issues. Checks system requirements, pending reboots, previous installations, and service states.

**Example**:
```bash
ansible-navigator run -m stdout diagnose_sql_install.yml -i hosts --eei=quay.io/truch/microsoft:3.2
```

---

### `attach_ansible_db.yml`

Attaches the ansible database if it exists as detached files on disk. Useful for recovering databases after file moves or server migrations.

**Example**:
```bash
ansible-navigator run -m stdout attach_ansible_db.yml -i hosts --eei=quay.io/truch/microsoft:3.2 \
  -e _mssql_login_password='YourPassword'
```

---

## Requirements

### Ansible Collections

```bash
ansible-galaxy collection install -r requirements_backup.yml
```

Collections needed:
- `ansible.windows` >= 2.0.0
- `community.windows` >= 2.0.0
- `lowlydba.sqlserver` >= 2.0.0 (for native backups)
- `cohesity.dataprotect` >= 1.4.4 (for Cohesity backups)

### Execution Environment

Use the custom execution environment that includes all required collections and dependencies:

```bash
quay.io/truch/microsoft:3.2
```

This EE includes:
- All required Ansible collections
- Python dependencies (pymssql, pywinrm)
- dbatools PowerShell module support
- Cohesity management SDK

To build the EE yourself, see `../../ansible-builder/EE_Microsoft/`.

### Windows Server Requirements

- Windows Server 2016+ (2019/2022 recommended)
- WinRM configured (HTTPS port 5986)
- PowerShell 5.1+
- For SQL Server: 2GB+ RAM, .NET Framework 4.5+
- For backups: dbatools PowerShell module (auto-installed by playbook)

### WinRM Setup

On the Windows server, run:
```powershell
# Enable WinRM with Basic auth over HTTPS
winrm quickconfig -force
winrm set winrm/config/service/auth '@{Basic="true"}'
winrm set winrm/config/service '@{AllowUnencrypted="false"}'

# Create self-signed certificate and enable HTTPS listener
# See ../windows_examples/winrm_setup.ps1 for complete setup script
```

---

## Additional Documentation

- [JINJA2_PATH_FIX.md](JINJA2_PATH_FIX.md) - Troubleshooting Jinja2 path escaping issues

---

## Backup Strategies

### Strategy 1: Full Backups Only (Simplest)
Daily full backups at 2 AM with 7-day retention.

```bash
# Cron: 0 2 * * *
ansible-navigator run -m stdout backup_mssql.yml -i hosts --eei=quay.io/truch/microsoft:3.2 \
  -e _mssql_login_password='Password'
```

**Pros**: Simple, independent backups  
**Cons**: Largest size, longest backup time  
**Recovery**: Single full backup

---

### Strategy 2: Full + Differential (Balanced)
Weekly full (Sunday) + daily differential (Monday-Saturday).

```bash
# Full on Sunday: 0 2 * * 0
ansible-navigator run -m stdout backup_mssql.yml -i hosts --eei=quay.io/truch/microsoft:3.2 \
  -e _backup_type=full -e _mssql_login_password='Password'

# Diff Mon-Sat: 0 2 * * 1-6
ansible-navigator run -m stdout backup_mssql.yml -i hosts --eei=quay.io/truch/microsoft:3.2 \
  -e _backup_type=diff -e _mssql_login_password='Password'
```

**Pros**: Faster daily backups, reasonable recovery time  
**Cons**: Need full + latest diff for restore  
**Recovery**: Last full + last differential

---

### Strategy 3: Full + Diff + Log (Production)
Weekly full + daily diff + hourly log backups.

```bash
# Full Sunday: 0 2 * * 0
# Diff Mon-Sat: 0 2 * * 1-6
# Log hourly: 0 * * * *
ansible-navigator run -m stdout backup_mssql.yml -i hosts --eei=quay.io/truch/microsoft:3.2 \
  -e _backup_type=log -e _mssql_login_password='Password'
```

**Pros**: Point-in-time recovery, minimal data loss  
**Cons**: Most complex, requires FULL recovery model  
**Recovery**: Full + diff + all logs since diff  
**Note**: Database must be in FULL recovery model

---

## Troubleshooting

### SQL Server won't install
```bash
# Check for pending reboots, prerequisites, previous installs
ansible-navigator run -m stdout diagnose_sql_install.yml -i hosts --eei=quay.io/truch/microsoft:3.2
```

### Database exists as files but not attached
```bash
# Attach database from existing files
ansible-navigator run -m stdout attach_ansible_db.yml -i hosts --eei=quay.io/truch/microsoft:3.2 \
  -e _mssql_login_password='Password'
```

### Backup fails with certificate error
The playbook auto-configures dbatools to trust SQL Server certificates. If issues persist, verify SQL Server is using HTTPS and certificates are valid.

### Restore fails with "database in use"
Use `_force=true` to disconnect all users and overwrite:
```bash
ansible-navigator run -m stdout restore_mssql.yml -i hosts --eei=quay.io/truch/microsoft:3.2 \
  -e _backup_file='C:\SQLBackups\db.bak' \
  -e _force=true \
  -e _mssql_login_password='Password'
```

---

## Related Examples

- [Windows Examples](../windows_examples/) - General Windows automation
- [Certificate Renewal Examples](../certificate_renewal_examples/) - Certificate management

---

## Support Files

- `create_demo_database.ps1` - PowerShell script for creating demo database
- `backup_example_vars.yml` - Example variables for backup playbook
- `backup_vault_template.yml` - Ansible Vault template for secrets
- `requirements_backup.yml` - Collection requirements
