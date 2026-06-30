# Certificate Discovery Examples

This directory contains playbooks and Ansible roles for discovering SSL/TLS certificates across different types of hosts and platforms.

## Overview

Certificate discovery is the first critical step in certificate lifecycle management. These examples demonstrate how to:

- Locate certificates on various operating systems and platforms
- Parse application configuration files to find certificate paths
- Identify certificate properties (expiration dates, subject, issuer, etc.)
- Generate comprehensive inventory reports of discovered certificates
- Support both Linux and Windows environments in a single playbook

## Architecture

This discovery system uses **Ansible roles** for modularity and reusability:

```
discovery/
├── playbooks/
│   └── discover_certificates.yml          # Unified playbook (RECOMMENDED)
├── roles/
│   ├── cert_discovery_config_based/       # Parse configs for cert paths
│   ├── cert_discovery_windows/            # Windows/IIS comprehensive discovery
│   └── cert_report_generator/             # Consolidate and format reports
├── inventory.yml                          # Sample inventory
├── filter_plugins/                        # Shared custom filters
├── templates/                             # Report templates
└── reports/                               # Generated reports (runtime)
```

## Supported Platforms

- **Linux Systems**: RHEL, CentOS, Rocky, Ubuntu, Debian
  - Apache HTTP Server (httpd, apache2)
  - Nginx
  - Tomcat (all versions)
  - HAProxy
  - Postfix, Dovecot
  - PostgreSQL, MySQL, MariaDB

- **Windows Systems**: Server 2019, 2022
  - Internet Information Services (IIS)
  - Certificate Stores (My, WebHosting, Root, CA)
  - SNI binding detection

## Quick Start

### Recommended: Unified Playbook

Run certificate discovery across **all hosts** (Linux and Windows) with one command:

```bash
cd playbooks
ansible-playbook -i ../inventory.yml discover_certificates.yml
```

This intelligent playbook:
- Detects the OS family automatically
- Identifies installed packages/services
- Routes to the appropriate discovery role
- Generates consolidated reports

### Target Specific Host Groups

```bash
# Linux hosts only
ansible-playbook -i ../inventory.yml discover_certificates.yml --limit linux_servers

# Windows hosts only
ansible-playbook -i ../inventory.yml discover_certificates.yml --limit windows_servers

# Specific host
ansible-playbook -i ../inventory.yml discover_certificates.yml --limit webserver01
```

### Override Discovery Strategy

```bash
# Force config-based discovery (default for auto-detection)
ansible-playbook -i ../inventory.yml discover_certificates.yml \
  -e cert_discovery_strategy=config_based

# Force Windows comprehensive discovery (certificate stores + IIS)
ansible-playbook -i ../inventory.yml discover_certificates.yml \
  -e cert_discovery_strategy=windows_comprehensive \
  --limit windows_servers

# Custom report directory
ansible-playbook -i ../inventory.yml discover_certificates.yml \
  -e cert_discovery_report_dir=/var/reports/certificates
```

## Discovery Methods

### Config-Based Discovery (Linux & Windows)

**How it works:**
1. Detects installed packages (Apache, Nginx, Tomcat, etc.)
2. Locates application configuration files
3. Parses configs using regex patterns to extract certificate directives
4. Validates certificate files exist
5. Extracts certificate properties using OpenSSL/PowerShell

**Advantages:**
- Most accurate (only finds actively used certificates)
- No filesystem scanning overhead
- Finds certificates in non-standard locations
- Tracks which application uses which certificate

**Example for Apache:**
```
Detected package: httpd
Config files: /etc/httpd/conf.d/ssl.conf
Regex pattern: ^\s*SSLCertificateFile\s+(.+)
Found: /etc/pki/tls/certs/server.crt
```

### Windows Comprehensive Discovery

**How it works:**
1. Scans Windows certificate stores
2. Queries IIS site bindings using PowerShell
3. Matches certificates to IIS sites
4. Detects SNI (Server Name Indication) configuration
5. Identifies orphaned certificates (in store but not bound)

**Stores scanned:**
- `Cert:\LocalMachine\My` (Personal certificates)
- `Cert:\LocalMachine\WebHosting` (Web hosting certificates)
- `Cert:\LocalMachine\Root` (Trusted root CAs)
- `Cert:\LocalMachine\CA` (Intermediate CAs)

## Output Reports

### Per-Host JSON Reports

```json
{
  "hostname": "webserver01",
  "os_family": "RedHat",
  "scan_method": "config_based",
  "scan_timestamp": "2026-06-30T14:30:22Z",
  "detected_packages": ["httpd", "postgresql"],
  "total_certificates": 3,
  "certificates": [
    {
      "path": "/etc/pki/tls/certs/server.crt",
      "type": "certificate",
      "config_source": "Apache HTTP Server",
      "subject": "CN=webserver01.example.com",
      "issuer": "CN=Example CA",
      "expiration": "Dec 31 23:59:59 2026 GMT",
      "days_to_expiry": 184,
      "serial_number": "01:23:45:67:89:AB:CD:EF"
    }
  ]
}
```

### Consolidated Reports

After discovery, consolidated reports are generated in JSON, CSV, and HTML formats:

```
reports/
├── webserver01_config_based_20260630T143022.json
├── winweb01_windows_comprehensive_20260630T143030.json
├── consolidated_cert_report_20260630T143045.json
├── consolidated_cert_report_20260630T143045.csv
└── consolidated_cert_report_20260630T143045.html  (interactive dashboard)
```

## Role-Based Usage

### Using Roles Directly in Playbooks

```yaml
---
- name: Custom Certificate Discovery
  hosts: webservers
  tasks:
    - name: Discover certificates
      ansible.builtin.include_role:
        name: cert_discovery_config_based
      vars:
        cert_discovery_report_dir: /var/reports/certs
        cert_discovery_expiry_warning_days: 30
```

### Role Dependencies in meta/main.yml

```yaml
dependencies:
  - role: cert_discovery_config_based
    vars:
      cert_discovery_report_dir: "{{ my_report_dir }}"
```

## Customization

### Adding Custom Applications

Extend discovery to support custom applications:

```yaml
# In group_vars/linux_servers.yml
cert_discovery_custom_package_configs:
  my_app:
    name: "My Custom App"
    config_files:
      - /etc/myapp/ssl.conf
      - /opt/myapp/config/*.conf
    cert_directives:
      - regex: 'ssl_certificate:\s+(.+)$'
        type: certificate
      - regex: 'ssl_certificate_key:\s+(.+)$'
        type: key
```

### Changing Expiration Thresholds

```bash
ansible-playbook discover_certificates.yml \
  -e cert_discovery_expiry_warning_days=90
```

## Integration with AAP/Tower

### Job Template Setup

**Job Template: Certificate Discovery - All Hosts**
- **Playbook**: `playbooks/discover_certificates.yml`
- **Inventory**: Production Servers
- **Credentials**: Machine credentials for Linux/Windows
- **Schedule**: Monthly (0 2 1 * *)
- **Extra Variables**:
  ```yaml
  cert_discovery_report_dir: /var/reports/certificates
  cert_discovery_expiry_warning_days: 60
  ```

### Workflow Template

```
┌──────────────────────────┐
│ Certificate Discovery    │
│ (All production hosts)   │
└─────────┬────────────────┘
          │
          ▼
┌──────────────────────────┐
│ Generate Reports         │
│ (Consolidate findings)   │
└─────────┬────────────────┘
          │
          ▼
┌──────────────────────────┐
│ Send Alert               │
│ (If certs expire <30d)   │
└──────────────────────────┘
```

## Best Practices

1. **Schedule Regular Discovery**: Run monthly to maintain certificate inventory
2. **Set Appropriate Thresholds**: 60-90 days for expiration warnings
3. **Use Service Accounts**: Dedicated read-only accounts for discovery
4. **Archive Reports**: Keep historical reports for compliance audits
5. **Integrate with CMDB**: Export reports to ServiceNow, Jira, etc.
6. **Alert on Critical Findings**: Configure notifications for expiring certificates
7. **Test in Dev First**: Validate discovery in non-production environments

## Integration with Renewal Workflows

The discovery system integrates with certificate renewal workflows:

1. **Discovery** → Identify expiring certificates
2. **Approval** → Generate renewal reports for review
3. **Renewal** → Execute renewal playbooks
4. **Verification** → Re-run discovery to confirm renewal

## Troubleshooting

### No certificates found on Linux

```bash
# Verify package detection
ansible linux_servers -m ansible.builtin.package_facts

# Check config file paths
ansible linux_servers -a "ls -la /etc/httpd/conf.d/"

# Run with verbose output
ansible-playbook discover_certificates.yml -vvv
```

### Windows discovery returns empty

```bash
# Test WinRM connectivity
ansible windows_servers -m ansible.windows.win_ping

# Check IIS installation
ansible windows_servers -m ansible.windows.win_powershell \
  -a "script='Get-WindowsFeature -Name Web-Server'"

# Verify certificate stores
ansible windows_servers -m ansible.windows.win_powershell \
  -a "script='Get-ChildItem Cert:\LocalMachine\My'"
```

### Permission errors

**Linux:**
```bash
# Grant read access to certificate directories
sudo setfacl -R -m u:ansible:r /etc/pki/tls/private
```

**Windows:**
```powershell
# Ensure service account has read access to certificate stores
# Usually granted automatically to Administrators group
```

## Legacy Playbooks

Previous standalone playbooks have been moved to `legacy_playbooks/` for reference:
- `config_based_cert_discovery.yml`
- `intelligent_cert_discovery.yml`
- `windows_comprehensive_cert_discovery.yml`
- `generate_consolidated_report.yml`

**Recommendation**: Use the new role-based `playbooks/discover_certificates.yml` instead.

## See Also

- [Role Documentation](roles/README.md)
- [Usage Guide](USAGE.md)
- [Windows/IIS Discovery Guide](WINDOWS_IIS_DISCOVERY.md)
- [Quick Reference](QUICK_REFERENCE.md)
- [Apache Renewal Examples](../apache/)
- [IIS Renewal Examples](../iis_windows/)
- [F5 Renewal Examples](../f5/)
- [Tomcat Renewal Examples](../tomcat_linux/)
