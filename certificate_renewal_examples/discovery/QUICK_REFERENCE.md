# Certificate Discovery - Quick Reference Card

## Choose Your Discovery Method

| Method | Best For | Command |
|--------|----------|---------|
| **Config-Based** (Recommended) | Production environments where you want accurate results from app configs | `ansible-playbook config_based_cert_discovery.yml` |
| **Intelligent** | Environments with many custom paths or when configs may not list all certs | `ansible-playbook intelligent_cert_discovery.yml` |
| **Windows Comprehensive** | Detailed Windows/IIS analysis including orphaned certs | `ansible-playbook windows_comprehensive_cert_discovery.yml` |

## Common Commands

```bash
# Basic discovery on all hosts
ansible-playbook -i inventory.yml config_based_cert_discovery.yml

# Linux only
ansible-playbook -i inventory.yml config_based_cert_discovery.yml --limit linux_servers

# Windows only
ansible-playbook -i inventory.yml config_based_cert_discovery.yml --limit windows_servers

# Single host
ansible-playbook -i inventory.yml config_based_cert_discovery.yml --limit webserver01

# Generate consolidated report
ansible-playbook generate_consolidated_report.yml

# Increase parallelism for large environments
ansible-playbook -i inventory.yml config_based_cert_discovery.yml --forks=20

# Verbose output for debugging
ansible-playbook -i inventory.yml config_based_cert_discovery.yml -vvv
```

## What Each Playbook Discovers

### config_based_cert_discovery.yml
- ✅ Parses Apache/Nginx/Tomcat/IIS configs
- ✅ Only reports certs actually configured in apps
- ✅ Shows which app uses which certificate
- ✅ Fastest and most accurate
- ❌ May miss certs not referenced in configs

**Output**: `hostname_config_based_TIMESTAMP.json`

### intelligent_cert_discovery.yml
- ✅ Detects installed packages
- ✅ Searches filesystem in standard locations
- ✅ Finds orphaned/unused certificates
- ✅ Works when configs are unavailable
- ❌ Slower due to filesystem searches

**Output**: `hostname_cert_inventory_TIMESTAMP.json`

### windows_comprehensive_cert_discovery.yml
- ✅ Scans all Windows certificate stores
- ✅ Identifies IIS bindings and certificates
- ✅ Finds orphaned certificates
- ✅ Flags expiring certificates
- ✅ Shows SNI configuration
- ❌ Windows/IIS only

**Output**: 
- `hostname_windows_comprehensive_TIMESTAMP.json`
- `hostname_windows_summary_TIMESTAMP.txt`

## Supported Applications

| Application | Linux Config-Based | Linux Intelligent | Windows |
|-------------|:------------------:|:-----------------:|:-------:|
| Apache (httpd) | ✅ | ✅ | ❌ |
| Nginx | ✅ | ✅ | ✅ |
| IIS | ❌ | ❌ | ✅ |
| Tomcat (all versions) | ✅ | ✅ | ✅ |
| HAProxy | ✅ | ✅ | ❌ |
| Postfix | ✅ | ✅ | ❌ |
| Dovecot | ✅ | ✅ | ❌ |
| PostgreSQL | ✅ | ✅ | ❌ |
| MySQL/MariaDB | ✅ | ✅ | ❌ |
| Windows Cert Stores | ❌ | ❌ | ✅ |

## Report Formats

All playbooks generate JSON reports. Use `generate_consolidated_report.yml` to create:

| Format | Use Case |
|--------|----------|
| **JSON** | Machine-readable, automation pipelines, SIEM integration |
| **CSV** | Spreadsheet analysis, Excel import, database import |
| **HTML** | Management dashboards, visual review, presentations |

## Configuration File Locations Checked

### Linux
```
Apache:     /etc/httpd/conf.d/*.conf, /etc/apache2/sites-enabled/*.conf
Nginx:      /etc/nginx/nginx.conf, /etc/nginx/conf.d/*.conf
Tomcat:     /etc/tomcat*/server.xml, /opt/tomcat*/conf/server.xml
HAProxy:    /etc/haproxy/haproxy.cfg
Postfix:    /etc/postfix/main.cf
Dovecot:    /etc/dovecot/conf.d/10-ssl.conf
PostgreSQL: /var/lib/postgresql/*/data/postgresql.conf
MySQL:      /etc/my.cnf, /etc/mysql/mysql.conf.d/*.cnf
```

### Windows
```
IIS:         applicationHost.config (via Get-WebBinding PowerShell)
Cert Stores: Cert:\LocalMachine\My, Cert:\LocalMachine\WebHosting
```

## Certificate Properties Extracted

- **Subject** (Common Name, Organization)
- **Issuer** (Certificate Authority)
- **Serial Number**
- **Thumbprint/Fingerprint**
- **Valid From / Valid Until** dates
- **Days to Expiry** (calculated)
- **Has Private Key** (yes/no)
- **DNS Names** (SANs - Subject Alternative Names)
- **Enhanced Key Usage** (Server Auth, Client Auth, etc.)
- **File Path** or **Store Location**

## Filtering Results

Edit the playbook variables to customize discovery:

```yaml
# Change certificate stores scanned (Windows)
certificate_stores:
  - My
  - WebHosting
  # - Root      # Uncomment to include root CAs

# Change expiration warning threshold
expiry_warning_days: 30  # Default: 60

# Change report output location
report_dir: "/var/reports/certificates"
```

## Integration Examples

### ServiceNow Integration
```bash
# Export to ServiceNow CMDB
ansible-playbook config_based_cert_discovery.yml \
  -e "export_to_servicenow=true" \
  -e "snow_instance=mycompany.service-now.com"
```

### Slack Notifications
```bash
# Alert on expiring certs
ansible-playbook generate_consolidated_report.yml \
  -e "slack_webhook=https://hooks.slack.com/..." \
  -e "expiry_threshold_days=30"
```

### Scheduled Execution (AAP/Tower)
```yaml
# Create scheduled job in AAP
Name: Monthly Certificate Discovery
Schedule: 0 2 1 * *  # 2 AM on 1st of each month
Playbook: config_based_cert_discovery.yml
Inventory: Production Servers
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No certificates found on Apache host | Verify package name: RHEL uses `httpd`, Ubuntu uses `apache2` |
| Permission denied reading certs | Grant Ansible user read access: `setfacl -R -m u:ansible:r /etc/pki/tls/private` |
| Windows discovery returns empty | Check WinRM: `ansible windows -m win_ping` |
| IIS bindings not found | Install Web-Scripting-Tools: `Install-WindowsFeature Web-Scripting-Tools` |
| Keystore files show as "protected" | Requires keytool and correct password (default: changeit) |

## Performance Tuning

| Environment Size | Recommended Settings |
|-----------------|---------------------|
| < 50 hosts | Default (forks=5) |
| 50-200 hosts | `--forks=10` |
| 200-1000 hosts | `--forks=20`, run during off-hours |
| 1000+ hosts | `--forks=30`, split into batches, use `--limit` |

Example for large environment:
```bash
# Batch 1: Web servers
ansible-playbook config_based_cert_discovery.yml --limit web_servers --forks=20

# Batch 2: App servers
ansible-playbook config_based_cert_discovery.yml --limit app_servers --forks=20

# Batch 3: Database servers
ansible-playbook config_based_cert_discovery.yml --limit db_servers --forks=20
```

## Security Best Practices

1. **Encrypt reports**: `ansible-vault encrypt reports/*.json`
2. **Limit access**: `chmod 600 reports/*.json`
3. **Use service accounts**: Dedicated read-only account for discovery
4. **Audit executions**: Log all discovery runs to syslog
5. **Secure transport**: Use SSH key authentication, not passwords

## Next Steps

After discovery, use the reports to:

1. **Identify expiring certificates** → Plan renewals
2. **Find orphaned certificates** → Clean up unused certs
3. **Verify certificate issuers** → Ensure all from trusted CAs
4. **Check for self-signed certs** → Replace in production
5. **Validate SNI configuration** → Optimize IIS bindings
6. **Update CMDB** → Sync with configuration management database

## See Full Documentation

- [Detailed Usage Guide](USAGE.md)
- [Windows/IIS Discovery Guide](WINDOWS_IIS_DISCOVERY.md)
- [Main README](README.md)
