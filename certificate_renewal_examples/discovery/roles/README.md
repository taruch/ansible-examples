## Certificate Discovery Roles

This directory contains Ansible roles for intelligent certificate discovery across multiple platforms and applications.

### Available Roles

This directory contains two discovery roles:

#### `cert_discovery_config_based`
**Primary discovery role** that parses application configuration files to find SSL/TLS certificates.

**Supported Platforms:**
- Linux (RHEL, CentOS, Rocky, Ubuntu, Debian)
- Windows (IIS)

**Supported Applications:**
- Apache HTTP Server (httpd, apache2)
- Nginx
- Tomcat (all versions)
- HAProxy
- Postfix
- Dovecot
- PostgreSQL
- MySQL/MariaDB
- IIS

**How it works:**
1. Detects installed packages
2. Locates and parses application config files
3. Extracts certificate paths from directives (SSLCertificateFile, ssl_certificate, etc.)
4. Validates certificates exist and extracts properties

**Variables:**
- `cert_discovery_report_dir`: Output directory for reports (default: `./reports`)
- `cert_discovery_expiry_warning_days`: Expiration threshold (default: 60)
- `cert_discovery_custom_package_configs`: Extend with custom application configs

---

#### `cert_discovery_windows`
**Comprehensive Windows-specific discovery** for IIS and certificate stores.

**Features:**
- Scans Windows certificate stores (My, WebHosting, Root, CA)
- Identifies IIS site bindings
- Detects SNI configuration
- Finds orphaned certificates
- Flags expiring certificates

**Variables:**
- `cert_discovery_certificate_stores`: Stores to scan (default: `['My', 'WebHosting', 'Root', 'CA']`)
- `cert_discovery_generate_text_summary`: Create human-readable summary (default: true)

---

### Usage

#### Option 1: Unified Playbook (Recommended)

Use the intelligent unified playbook that automatically selects the appropriate role:

```bash
cd playbooks
ansible-playbook -i ../inventory.yml discover_certificates.yml
```

The playbook will:
- Detect the OS family (Linux vs Windows)
- Check for installed packages/services
- Route to the appropriate discovery role
- Generate a consolidated report

#### Option 2: Direct Role Usage

Use roles directly in your own playbooks:

```yaml
---
- name: Custom Certificate Discovery
  hosts: webservers
  tasks:
    - name: Discover certificates on web servers
      ansible.builtin.include_role:
        name: cert_discovery_config_based
      vars:
        cert_discovery_report_dir: /var/reports/certs
        cert_discovery_expiry_warning_days: 30
```

#### Option 3: Role Dependencies

Include as a dependency in your own roles:

```yaml
# meta/main.yml
dependencies:
  - role: cert_discovery_config_based
    vars:
      cert_discovery_report_dir: "{{ my_report_dir }}"
```

### Customization

#### Adding Custom Package Configurations

Extend the config-based discovery with custom applications:

```yaml
# In your playbook or group_vars
cert_discovery_custom_package_configs:
  myapp:
    name: "My Custom Application"
    config_files:
      - /etc/myapp/ssl.conf
      - /opt/myapp/config/*.conf
    cert_directives:
      - regex: 'certificate:\s+(.+)$'
        type: certificate
      - regex: 'private_key:\s+(.+)$'
        type: key
```

#### Changing Discovery Strategy

Force a specific discovery method:

```yaml
# In playbooks/discover_certificates.yml
vars:
  cert_discovery_strategy: windows_comprehensive  # Force Windows comprehensive
  # OR
  cert_discovery_strategy: config_based           # Force config-based
  # OR
  cert_discovery_strategy: auto                   # Auto-detect (default)
```

### Integration with AAP/Tower

#### Job Template Setup

**Template 1: Unified Discovery**
```yaml
Name: Certificate Discovery - All Hosts
Playbook: playbooks/discover_certificates.yml
Inventory: Production Servers
Schedule: Monthly (0 2 1 * *)
Extra Vars:
  cert_discovery_report_dir: /var/reports/certificates
  cert_discovery_expiry_warning_days: 60
```

**Template 2: Linux Only**
```yaml
Name: Certificate Discovery - Linux
Playbook: playbooks/discover_certificates.yml
Inventory: Production Servers
Limit: linux_servers
Extra Vars:
  cert_discovery_strategy: config_based
```

**Template 3: Windows Only**
```yaml
Name: Certificate Discovery - Windows
Playbook: playbooks/discover_certificates.yml
Inventory: Production Servers
Limit: windows_servers
Extra Vars:
  cert_discovery_strategy: windows_comprehensive
```

#### Workflow Example

```
┌─────────────────────────┐
│ Certificate Discovery   │
│ (All Hosts)             │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Generate Reports        │
│ (Localhost)             │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Email Report to Team    │
│ (If expiring certs)     │
└─────────────────────────┘
```

### Output Files

Each role generates JSON reports in `cert_discovery_report_dir`:

**Config-Based Discovery:**
```
reports/
├── webserver01_config_based_20260630T143022.json
├── webserver02_config_based_20260630T143025.json
└── ...
```

**Windows Comprehensive:**
```
reports/
├── winweb01_windows_comprehensive_20260630T143030.json
├── winweb01_windows_summary_20260630T143030.txt
└── ...
```

**Consolidated Reports:**
```
reports/
├── consolidated_cert_report_20260630T143045.json
├── consolidated_cert_report_20260630T143045.csv
└── consolidated_cert_report_20260630T143045.html
```

### Report Structure

```json
{
  "hostname": "webserver01",
  "os_family": "RedHat",
  "scan_method": "config_based",
  "detected_packages": ["httpd", "postgresql"],
  "total_certificates": 3,
  "certificates": [
    {
      "path": "/etc/pki/tls/certs/server.crt",
      "type": "certificate",
      "subject": "CN=webserver01.example.com",
      "issuer": "CN=Example CA",
      "expiration": "Dec 31 23:59:59 2026 GMT",
      "serial_number": "01234567890ABCDEF"
    }
  ]
}
```

### Best Practices

1. **Schedule Regular Discovery**: Run monthly to maintain certificate inventory
2. **Set Appropriate Thresholds**: 60-90 days for expiration warnings
3. **Archive Reports**: Keep historical reports for compliance
4. **Integrate with CMDB**: Export to ServiceNow, Jira, or similar
5. **Alert on Findings**: Configure notifications for expiring certificates
6. **Use Service Accounts**: Dedicated read-only accounts for discovery
7. **Test in Dev First**: Validate discovery in non-production before rolling out

### Troubleshooting

**No certificates found on Linux:**
- Check package names match your distribution (httpd vs apache2)
- Verify config file paths in `cert_discovery_package_configs`
- Run with `-vvv` for verbose output

**Windows discovery returns empty:**
- Verify WinRM connectivity: `ansible windows -m win_ping`
- Check IIS is installed: `Get-WindowsFeature -Name Web-Server`
- Ensure Web-Scripting-Tools feature is installed

**Permission denied errors:**
- Grant Ansible user read access to certificate directories
- Use setfacl on Linux: `setfacl -R -m u:ansible:r /etc/pki/tls/private`
- Check Windows certificate store permissions

### See Also

- [Main Discovery README](../README.md)
- [Usage Guide](../USAGE.md)
- [Windows/IIS Discovery Guide](../WINDOWS_IIS_DISCOVERY.md)
- [Quick Reference](../QUICK_REFERENCE.md)
