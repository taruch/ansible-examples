# Certificate Discovery - Usage Guide

## Overview

The intelligent certificate discovery playbook automatically detects installed packages on hosts and identifies certificate locations by parsing configuration files rather than performing filesystem searches. This makes discovery more accurate and efficient.

## Quick Start

### 1. Basic Discovery

Run discovery against all hosts in your inventory:

```bash
ansible-playbook -i inventory.yml intelligent_cert_discovery.yml
```

### 2. Target Specific Host Groups

Discover certificates only on Linux servers:

```bash
ansible-playbook -i inventory.yml intelligent_cert_discovery.yml --limit linux_servers
```

Discover certificates only on Windows servers:

```bash
ansible-playbook -i inventory.yml intelligent_cert_discovery.yml --limit windows_servers
```

### 3. Generate Consolidated Report

After running discovery, generate a consolidated report:

```bash
ansible-playbook generate_consolidated_report.yml
```

This creates:
- **JSON report**: Machine-readable full details
- **CSV report**: Spreadsheet-compatible for analysis
- **HTML report**: Visual dashboard for management

## How It Works

### Package Detection Phase

1. **Linux**: Uses `ansible.builtin.package_facts` to identify installed packages
2. **Windows**: Queries Windows Features and installed programs

### Configuration Parsing Phase

Rather than searching directories, the playbook:

1. Identifies relevant packages (Apache, Nginx, Tomcat, etc.)
2. Locates and parses the configuration files for each package
3. Extracts certificate paths directly from the configuration
4. Validates that the certificates exist at the configured locations

### Certificate Analysis Phase

For each discovered certificate:
- Extracts subject, issuer, and expiration date
- Calculates days until expiry
- Identifies associated private keys
- Detects certificate format (PEM, DER, PKCS12, JKS)

## Supported Applications

### Web Servers
- **Apache HTTP Server** (httpd/apache2)
  - Parses: `/etc/httpd/conf.d/*.conf`, `/etc/apache2/sites-enabled/*.conf`
  - Extracts: `SSLCertificateFile`, `SSLCertificateKeyFile`, `SSLCACertificateFile`

- **Nginx**
  - Parses: `/etc/nginx/nginx.conf`, `/etc/nginx/sites-enabled/*`, `/etc/nginx/conf.d/*.conf`
  - Extracts: `ssl_certificate`, `ssl_certificate_key`, `ssl_trusted_certificate`

### Application Servers
- **Tomcat** (all versions)
  - Parses: `server.xml`, `context.xml`
  - Extracts: keystoreFile, truststoreFile from `<Connector>` elements

- **JBoss/WildFly**
  - Parses: `standalone.xml`, `domain.xml`
  - Extracts: keystore paths from security realms

### Databases
- **PostgreSQL**
  - Parses: `postgresql.conf`
  - Extracts: `ssl_cert_file`, `ssl_key_file`, `ssl_ca_file`

- **MySQL/MariaDB**
  - Parses: `my.cnf`, `/etc/mysql/mysql.conf.d/*.cnf`
  - Extracts: `ssl-cert`, `ssl-key`, `ssl-ca`

### Load Balancers
- **HAProxy**
  - Parses: `/etc/haproxy/haproxy.cfg`
  - Extracts: `crt` and `ca-file` from bind statements

### Mail Servers
- **Postfix**
  - Parses: `main.cf`
  - Extracts: `smtpd_tls_cert_file`, `smtpd_tls_key_file`

- **Dovecot**
  - Parses: `dovecot.conf`, `conf.d/10-ssl.conf`
  - Extracts: `ssl_cert`, `ssl_key`

### Windows
- **IIS**
  - Queries: IIS bindings via PowerShell
  - Retrieves: Certificate thumbprints and resolves to cert store locations

- **Windows Certificate Stores**
  - Scans: LocalMachine\My, LocalMachine\WebHosting, LocalMachine\Root
  - Identifies: Certificates with private keys

## Output Format

### Individual Host Reports

Each host generates a JSON report in `./reports/`:

```json
{
  "hostname": "webserver01",
  "fqdn": "webserver01.example.com",
  "ip_address": "192.168.1.10",
  "os_family": "RedHat",
  "detected_packages": ["httpd", "postgresql"],
  "certificates": [
    {
      "path": "/etc/pki/tls/certs/server.crt",
      "discovered_via": "httpd:SSLCertificateFile:/etc/httpd/conf.d/ssl.conf",
      "subject": "CN=webserver01.example.com",
      "issuer": "CN=Example CA",
      "expiration": "Dec 31 23:59:59 2026 GMT",
      "days_to_expiry": 180,
      "has_private_key": true,
      "private_key_path": "/etc/pki/tls/private/server.key"
    }
  ]
}
```

### Consolidated Report

Aggregates all host reports with:
- Total certificate inventory across all hosts
- Expiration timeline analysis
- Certificates grouped by issuer/CA
- Hosts grouped by OS family
- High-risk certificates flagged (expiring < 30 days)

## Customization

### Add Custom Package Mappings

Edit `intelligent_cert_discovery.yml` to add support for additional applications:

```yaml
package_config_paths:
  myapp:
    config_files:
      - /etc/myapp/ssl.conf
      - /opt/myapp/config/certificates.yaml
    cert_patterns:
      - 'certificate_path:\s+(.+)'
      - 'key_path:\s+(.+)'
```

### Adjust Report Output

Modify report location and formats in variables:

```yaml
vars:
  report_dir: "/var/reports/certificates"
  output_formats:
    - json
    - csv
    - html
    - syslog  # Send to syslog for SIEM integration
```

### Schedule Automated Discovery

Add to crontab for monthly discovery:

```cron
0 2 1 * * cd /path/to/playbooks && ansible-playbook intelligent_cert_discovery.yml
```

Or create an AAP scheduled job for regular execution.

## Performance Considerations

### Efficiency Features

1. **Configuration-based discovery**: Only checks paths explicitly configured in applications (no filesystem scans)
2. **Parallel execution**: Uses Ansible's parallelism to scan multiple hosts simultaneously
3. **Selective certificate parsing**: Only parses certificates once they're identified in configs
4. **Cached package facts**: Package detection runs once per host

### Tuning Options

For large environments (100+ hosts):

```bash
# Increase parallelism (default is 5)
ansible-playbook -i inventory.yml intelligent_cert_discovery.yml --forks=20

# Limit to specific paths if you know where certs are
ansible-playbook intelligent_cert_discovery.yml -e "scan_only_configs=true"
```

## Integration Examples

### Export to CMDB

```bash
# Export to ServiceNow
ansible-playbook intelligent_cert_discovery.yml \
  -e "export_to_servicenow=true" \
  -e "snow_instance=mycompany.service-now.com"

# Export to Jira
ansible-playbook intelligent_cert_discovery.yml \
  -e "export_to_jira=true" \
  -e "jira_project=CERTMGMT"
```

### Alert on Expiring Certificates

```bash
# Send Slack notification for certs expiring < 30 days
ansible-playbook generate_consolidated_report.yml \
  -e "slack_webhook=https://hooks.slack.com/..." \
  -e "expiry_threshold_days=30"
```

## Troubleshooting

### Common Issues

**Issue**: No certificates found on a host with web services

**Solution**: Check that the package name matches your distribution:
- RHEL/CentOS use `httpd`, Ubuntu uses `apache2`
- Add debug output: `-vvv` flag to see which packages were detected

**Issue**: Permission denied reading certificate files

**Solution**: Ensure the Ansible user has read access:
```bash
# Grant read access to automation account
sudo setfacl -R -m u:ansible:r /etc/pki/tls/private
```

**Issue**: Windows certificate discovery returns empty

**Solution**: Verify WinRM connectivity and PowerShell remoting:
```bash
ansible windows_servers -m win_ping
```

### Debug Mode

Run with verbose output to troubleshoot:

```bash
ansible-playbook -i inventory.yml intelligent_cert_discovery.yml -vvv
```

Check detected packages:

```bash
ansible-playbook -i inventory.yml intelligent_cert_discovery.yml --tags package_detection
```

## Security Best Practices

1. **Limit access to reports**: Certificate inventory reveals infrastructure details
   ```bash
   chmod 600 reports/*.json
   ```

2. **Use vault for credentials**: Encrypt inventory passwords
   ```bash
   ansible-vault encrypt inventory.yml
   ```

3. **Audit discovery runs**: Log all executions
   ```bash
   ansible-playbook intelligent_cert_discovery.yml 2>&1 | \
     logger -t cert-discovery
   ```

4. **Rotate service accounts**: Use dedicated accounts for discovery with read-only access

## See Also

- [Apache Renewal Workflow](../apache/README.md)
- [Windows IIS Renewal](../iis_windows/README.md)
- [F5 Load Balancer Certificates](../f5/README.md)
