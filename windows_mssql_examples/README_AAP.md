# SQL Server Automation in Ansible Automation Platform

This directory contains playbooks for automating Microsoft SQL Server operations in Ansible Automation Platform (AAP).

## Overview

Automated SQL Server lifecycle management:
- **Deploy**: Download and install SQL Server 2022 from Microsoft
- **Create**: Create databases with sample data
- **Backup**: Native SQL backup or Cohesity integration
- **Restore**: Point-in-time recovery and database restoration
- **Workflow**: End-to-end deployment pipeline

## Quick Start

### 1. Prerequisites

**AAP Controller:**
- Ansible Automation Platform 2.4+
- Access to AAP controller API
- Organization created

**Project:**
- Create SCM project pointing to this repository
- Ensure `windows_mssql_examples/` directory is accessible

**Inventory:**
- Windows inventory with hosts configured
- WinRM connectivity tested
- Hosts must have Windows Server 2016+ with .NET Framework 4.5+

**Execution Environment:**
- Custom EE with Windows collections required
- Recommended: `quay.io/truch/microsoft:3.3`
- Must include:
  - `ansible.windows`
  - `community.windows`
  - `lowlydba.sqlserver` (for backup/restore)

### 2. Run AAP Setup

```bash
# Configure AAP with SQL Server job templates
ansible-playbook setup.yml

# Or specify custom values
ansible-playbook setup.yml \
  -e "aap_organization='IT Operations'" \
  -e "aap_project='SQL Automation'" \
  -e "aap_inventory='Windows Servers'"
```

The setup playbook creates:
- **Custom Credential Type**: SQL Server Credential
- **Credentials**: SQL Server SA credential
- **4 Job Templates**: Deploy, Create DB, Backup, Restore
- **1 Workflow Template**: Full Setup (Deploy → Create → Backup)

### 3. Update Credentials

After running `setup.yml`, update the SQL Server SA password in AAP:

1. Navigate to **Resources → Credentials**
2. Edit **SQL Server SA Credential**
3. Update the **SQL Server Login Password** field
4. Save

### 4. Test the Workflow

Run the end-to-end workflow:

1. Navigate to **Resources → Templates**
2. Launch **MSSQL | Full Setup Workflow**
3. Select target Windows host (limit)
4. Provide variables:
   ```yaml
   mssql_sa_password: "YourSecurePassword123!"
   ```
5. Launch

The workflow will:
1. Deploy SQL Server 2022 Developer Edition
2. Create demo database with sample data
3. Perform initial full backup

## Job Templates

### 1. Deploy SQL Server 2022

**Template Name**: `MSSQL | Deploy SQL Server 2022`

Automated deployment of SQL Server from Microsoft downloads.

**Required Variables:**
- `mssql_sa_password`: SA account password

**Optional Variables:**
- `sql_version`: Version to install (default: `2022`)
- `mssql_max_memory_mb`: Max server memory (default: `4096`)
- `mssql_data_dir`: Data directory (default: `C:\SQLData`)
- `mssql_log_dir`: Log directory (default: `C:\SQLLogs`)
- `mssql_tcp_port`: TCP port (default: `1433`)

**Example Extra Vars:**
```yaml
mssql_sa_password: "SecurePassword123!"
mssql_max_memory_mb: 8192
mssql_data_dir: "D:\\SQLData"
```

**What it does:**
1. Downloads SQL Server bootstrap installer from Microsoft CDN
2. Downloads SQL Server 2022 Developer Edition ISO
3. Installs SQL Server via scheduled task (bypasses WinRM limitations)
4. Configures TCP/IP protocol
5. Sets max server memory
6. Opens firewall ports (1433, 1434)
7. Starts all SQL Server services
8. Verifies installation

**Estimated Duration**: 10-15 minutes

---

### 2. Create Demo Database

**Template Name**: `MSSQL | Create Demo Database`

Creates a demo database with sample data for testing.

**Required Credentials:**
- SQL Server Credential

**Optional Variables:**
- `database_name`: Database name (default: `ansible`)
- `mssql_instance`: SQL Server instance (default: `localhost`)

**Example Extra Vars:**
```yaml
database_name: "TestDB"
```

**What it does:**
1. Creates database
2. Creates tables: Users, Products, Orders
3. Creates view: vw_OrderSummary
4. Populates with sample data (10 users, 15 products, 15 orders)

**Sample Data:**
- **Users**: IT, Sales, HR, Engineering departments
- **Products**: Servers, software licenses, hardware
- **Orders**: Various statuses (Pending, Shipped, Delivered, Cancelled)

**Estimated Duration**: 1-2 minutes

---

### 3. Backup Database

**Template Name**: `MSSQL | Backup Database`

Backup SQL Server databases using native backup or Cohesity.

**Required Credentials:**
- SQL Server Credential

**Variables:**
- `backup_method`: `native` or `cohesity` (default: `native`)
- `backup_type`: `full`, `diff`, or `log` (default: `full`)
- `mssql_database`: Database name or `all` (default: `all`)
- `backup_path`: Backup directory (default: `C:\SQLBackups`)
- `backup_compression`: Enable compression (default: `true`)
- `backup_verify`: Verify after backup (default: `true`)
- `backup_retention_days`: Retention days (default: `7`)

**Example Extra Vars:**
```yaml
backup_type: full
mssql_database: ansible
backup_path: "D:\\Backups"
backup_compression: true
backup_verify: true
backup_retention_days: 14
```

**What it does:**
1. Installs dbatools PowerShell module (if needed)
2. Validates SQL Server is running
3. Performs backup (full, differential, or transaction log)
4. Verifies backup integrity (if enabled)
5. Cleans up old backups based on retention policy

**Estimated Duration**: 2-5 minutes (depends on database size)

---

### 4. Restore Database

**Template Name**: `MSSQL | Restore Database`

Restore SQL Server databases from backup files.

**Required Credentials:**
- SQL Server Credential

**Required Variables:**
- `backup_file`: Full path to backup file (e.g., `C:\SQLBackups\ansible_backup.bak`)

**Optional Variables:**
- `mssql_database`: Target database name (default: from backup)
- `restore_with_replace`: Overwrite existing (default: `false`)
- `restore_with_recovery`: Leave operational (default: `true`)

**Example Extra Vars:**
```yaml
backup_file: "C:\\SQLBackups\\ansible_20260618_150000.bak"
mssql_database: "ansible_restored"
restore_with_replace: false
```

**What it does:**
1. Validates backup file exists
2. Reads backup file header
3. Restores database
4. Verifies restore success

**Estimated Duration**: 2-5 minutes (depends on backup size)

---

## Workflow Template

### Full Setup Workflow

**Template Name**: `MSSQL | Full Setup Workflow`

End-to-end SQL Server deployment pipeline.

**Flow:**
```
┌─────────────────────┐
│ Deploy SQL Server   │
└──────────┬──────────┘
           │ Success
           ▼
┌─────────────────────┐
│ Create Demo DB      │
└──────────┬──────────┘
           │ Success
           ▼
┌─────────────────────┐
│ Backup Database     │
└─────────────────────┘
```

**Variables:**
```yaml
mssql_sa_password: "SecurePassword123!"
database_name: "ansible"
backup_type: "full"
```

**Total Duration**: 15-20 minutes

---

## Credentials

### SQL Server Credential

Custom credential type for SQL authentication.

**Fields:**
- `mssql_login_user`: SQL Server login username (e.g., `sa`)
- `mssql_login_password`: Password (secret)

**Injected Variables:**
- `_mssql_login_user`
- `_mssql_login_password`

**Usage in Job Templates:**
Automatically injected into playbook extra vars.

---

## Variables Reference

### Common Variables

Available in all job templates:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `_hosts` | Target hosts pattern | `windows` | No |
| `mssql_instance` | SQL Server instance | `localhost` | No |
| `_mssql_login_user` | SQL login user | `sa` | Yes (credential) |
| `_mssql_login_password` | SQL password | - | Yes (credential) |

### Deploy-Specific Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `sql_version` | SQL Server version | `2022` |
| `mssql_sa_password` | SA password | - (required) |
| `mssql_instance_name` | Instance name | `MSSQLSERVER` |
| `mssql_tcp_port` | TCP port | `1433` |
| `mssql_max_memory_mb` | Max memory (MB) | `4096` |
| `mssql_data_dir` | Data directory | `C:\SQLData` |
| `mssql_log_dir` | Log directory | `C:\SQLLogs` |

### Backup-Specific Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `backup_method` | `native` or `cohesity` | `native` |
| `backup_type` | `full`, `diff`, `log` | `full` |
| `backup_path` | Backup directory | `C:\SQLBackups` |
| `backup_compression` | Enable compression | `true` |
| `backup_verify` | Verify after backup | `true` |
| `backup_retention_days` | Days to keep backups | `7` |

### Restore-Specific Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `backup_file` | Path to backup file | - (required) |
| `restore_with_replace` | Overwrite existing DB | `false` |
| `restore_with_recovery` | Leave DB operational | `true` |

---

## Troubleshooting

### SQL Server Installation Fails

**Symptom**: Deploy job fails with DPAPI or "Access denied" errors

**Solution**: The playbook uses a scheduled task approach to bypass WinRM session limitations. If this fails:
1. Check Windows Server version (requires 2016+)
2. Verify .NET Framework 4.5+ is installed
3. Check `C:\Temp\sql_install_log.txt` on target host
4. Review Summary.txt in `C:\Program Files\Microsoft SQL Server\160\Setup Bootstrap\Log\`

### Backup Job Fails - Module Not Found

**Symptom**: "dbatools module not found"

**Solution**: The playbook auto-installs dbatools. If it fails:
1. Check internet connectivity from Windows host
2. Manually install: `Install-Module -Name dbatools -Force`
3. Verify execution environment has `lowlydba.sqlserver` collection

### Credential Injection Not Working

**Symptom**: Variables like `_mssql_login_password` are empty

**Solution**:
1. Verify credential is attached to job template
2. Check custom credential type was created correctly
3. Ensure injector mapping matches variable names

### WinRM Connection Issues

**Symptom**: "Unable to connect via WinRM"

**Solution**:
1. Test WinRM from AAP: `ansible windows -m win_ping`
2. Verify WinRM ports (5985/5986) are open
3. Check Windows credential in AAP
4. Ensure `ansible_winrm_*` variables are set in inventory

---

## Best Practices

### Security

1. **Credentials**:
   - Use separate credentials for different environments (dev, prod)
   - Rotate SA password regularly
   - Consider using Windows authentication instead of SQL auth

2. **Execution Environment**:
   - Pin to specific EE version for consistency
   - Test EE updates in dev before production

3. **Variables**:
   - Store sensitive data in AAP credentials, not extra vars
   - Use surveys to prompt for required variables
   - Set variable defaults in job templates

### Operations

1. **Testing**:
   - Test playbooks in dev environment first
   - Use limit patterns to target specific hosts
   - Run check mode when available

2. **Monitoring**:
   - Review job output logs
   - Set up notifications for job failures
   - Monitor Windows event logs during deployments

3. **Backup Strategy**:
   - Schedule regular backups via AAP schedules
   - Implement 3-2-1 backup rule (3 copies, 2 media types, 1 offsite)
   - Test restores regularly
   - Document recovery procedures

---

## Advanced Usage

### Custom Workflows

Create custom workflows combining SQL Server operations:

**Example: Database Refresh Workflow**
```
1. Backup production database
2. Restore to dev server (with different name)
3. Sanitize data (custom playbook)
4. Notify team
```

### Integration with Other Systems

**ServiceNow Integration:**
- Trigger SQL deployment from ServiceNow request
- Update CMDB with SQL Server details
- Notify requestor on completion

**Monitoring Integration:**
- Trigger backup after detecting database changes
- Auto-remediate SQL service failures
- Alert on backup failures

### Schedules

Create AAP schedules for:
- **Daily**: Transaction log backups (8 AM, 12 PM, 4 PM, 8 PM)
- **Nightly**: Full database backups (2 AM)
- **Weekly**: Differential backups (Sunday 2 AM)
- **Monthly**: Database maintenance (1st Sunday, 3 AM)

---

## Files Reference

| File | Purpose |
|------|---------|
| `setup.yml` | AAP configuration playbook |
| `deploy_mssql.yml` | SQL Server installation |
| `create_demo_database.yml` | Demo database creation |
| `backup_mssql.yml` | Database backup (native/Cohesity) |
| `restore_mssql.yml` | Database restore |
| `files/create_demo_database.ps1` | PowerShell script for demo data |
| `requirements_backup.yml` | Ansible collections for backup |

---

## Support

For issues or questions:
1. Check AAP job output logs
2. Review Windows event logs on target hosts
3. Examine SQL Server error logs
4. Check this README and inline playbook comments

---

## License

These playbooks are examples for educational and demonstration purposes.
