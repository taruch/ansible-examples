# Windows and IIS Certificate Discovery Guide

## Overview

Discovering certificates on Windows/IIS hosts works differently from Linux because Windows uses centralized certificate stores rather than file-based certificates. This guide explains the discovery methods and how to use the playbooks.

## Windows Certificate Architecture

### Certificate Store Locations

Windows organizes certificates in hierarchical stores:

```
Cert:\
├── LocalMachine\
│   ├── My                  # Personal certificates (with private keys)
│   ├── WebHosting          # IIS web hosting certificates
│   ├── Root                # Trusted root CAs
│   ├── CA                  # Intermediate CAs
│   ├── TrustedPublisher    # Trusted publishers
│   └── AuthRoot            # Third-party root CAs
└── CurrentUser\
    ├── My                  # User's personal certificates
    ├── Root                # User's trusted roots
    └── ...
```

### IIS Certificate Binding

IIS doesn't store certificates directly. Instead, it:
1. References certificates by **thumbprint** (SHA1 hash)
2. Stores the thumbprint in site binding configuration
3. Resolves the certificate from the Windows certificate store at runtime

## Discovery Methods

### Method 1: Query IIS Bindings (Recommended)

The `config_based_cert_discovery.yml` playbook uses this method:

```powershell
# This is what the playbook does automatically
Import-Module WebAdministration

# Get all HTTPS bindings with certificates
Get-WebBinding | Where-Object {
    $_.protocol -eq 'https' -and $_.certificateHash
} | ForEach-Object {
    $certHash = $_.certificateHash
    $storeName = if ($_.certificateStoreName) { $_.certificateStoreName } else { 'My' }
    $cert = Get-ChildItem -Path "Cert:\LocalMachine\$storeName" |
            Where-Object { $_.Thumbprint -eq $certHash }

    [PSCustomObject]@{
        SiteName = $_.ItemXPath -replace '.*name=''([^'']+)''.*', '$1'
        BindingInfo = $_.bindingInformation
        CertThumbprint = $certHash
        CertStore = "Cert:\LocalMachine\$storeName"
        Subject = $cert.Subject
        Issuer = $cert.Issuer
        Expiration = $cert.NotAfter
        HasPrivateKey = $cert.HasPrivateKey
    }
}
```

**This method finds**:
- Only certificates actively used by IIS sites
- The exact binding (IP:port) using each certificate
- Which site uses which certificate

### Method 2: Scan Certificate Stores

For certificates not currently bound to IIS:

```powershell
# Scan all stores for certificates with private keys
$stores = @('My', 'WebHosting')
foreach ($store in $stores) {
    Get-ChildItem -Path "Cert:\LocalMachine\$store" |
    Where-Object { $_.HasPrivateKey } |
    Select-Object Thumbprint, Subject, Issuer, NotAfter
}
```

**This method finds**:
- All certificates with private keys (potential server certificates)
- Certificates installed but not yet bound to IIS
- Orphaned certificates from decommissioned sites

### Method 3: Parse IIS ApplicationHost.config

Direct configuration file parsing:

```xml
<!-- C:\Windows\System32\inetsrv\config\applicationHost.config -->
<configuration>
  <system.applicationHost>
    <sites>
      <site name="Default Web Site" id="1">
        <bindings>
          <binding protocol="https"
                   bindingInformation="*:443:"
                   certificateHash="ABC123..."
                   certificateStoreName="My" />
        </bindings>
      </site>
    </sites>
  </system.applicationHost>
</configuration>
```

**This method provides**:
- Configuration as stored on disk
- Historical bindings (if config backups exist)
- Site configuration independent of IIS service state

## Using the Playbooks

### Quick Discovery (IIS Only)

Run the configuration-based discovery which focuses on IIS:

```bash
ansible-playbook -i inventory.yml config_based_cert_discovery.yml \
  --limit windows_servers
```

This produces a report showing:
```json
{
  "hostname": "winweb01",
  "scan_method": "iis_configuration_parsing",
  "iis_installed": true,
  "total_certificates": 3,
  "iis_bindings": [
    {
      "SiteName": "Default Web Site",
      "BindingInformation": "*:443:",
      "CertificateHash": "ABC123DEF456...",
      "CertificateStore": "Cert:\\LocalMachine\\My",
      "Subject": "CN=www.example.com",
      "Issuer": "CN=DigiCert SHA2 Secure Server CA",
      "NotAfter": "2026-12-31 23:59:59",
      "HasPrivateKey": true,
      "DnsNameList": "www.example.com,example.com"
    }
  ]
}
```

### Comprehensive Discovery (All Certificate Stores)

Create a dedicated Windows discovery playbook:

```bash
ansible-playbook windows_comprehensive_cert_discovery.yml
```

This scans:
- IIS bindings
- LocalMachine\My (personal certificates)
- LocalMachine\WebHosting (IIS certificates)
- LocalMachine\CA (intermediate CAs)
- Identifies orphaned certificates
- Checks for expiring certificates

## Manual Discovery on Windows

### PowerShell Commands

Connect to your Windows server and run:

```powershell
# 1. Check IIS version and status
Get-WindowsFeature -Name Web-Server
Get-Service -Name W3SVC

# 2. List all IIS sites and their bindings
Import-Module WebAdministration
Get-Website | Select-Object Name, State, Bindings

# 3. Get detailed binding information
Get-WebBinding | Format-Table protocol, bindingInformation, certificateHash

# 4. View certificate details for a specific thumbprint
$thumbprint = "ABC123DEF456..."
Get-ChildItem -Path Cert:\LocalMachine\My |
    Where-Object { $_.Thumbprint -eq $thumbprint } |
    Select-Object Subject, Issuer, NotAfter, HasPrivateKey, @{
        Name='DnsNames'; Expression={$_.DnsNameList.Unicode -join ', '}
    }

# 5. Find all certificates expiring soon
$daysThreshold = 60
Get-ChildItem -Path Cert:\LocalMachine\My |
    Where-Object {
        $_.NotAfter -lt (Get-Date).AddDays($daysThreshold) -and
        $_.HasPrivateKey
    } |
    Select-Object Subject, NotAfter, Thumbprint |
    Sort-Object NotAfter

# 6. Export certificate inventory to CSV
Get-ChildItem -Path Cert:\LocalMachine\My |
    Select-Object Subject, Issuer, Thumbprint,
        @{Name='NotAfter'; Expression={$_.NotAfter.ToString('yyyy-MM-dd')}},
        HasPrivateKey |
    Export-Csv -Path C:\temp\cert_inventory.csv -NoTypeInformation
```

### Finding Which Sites Use Which Certificates

```powershell
# Create a mapping of certificates to IIS sites
$certToSite = @{}

Get-WebBinding | Where-Object { $_.protocol -eq 'https' } | ForEach-Object {
    $siteName = $_.ItemXPath -replace '.*name=''([^'']+)''.*', '$1'
    $certHash = $_.certificateHash

    if ($certHash) {
        if (-not $certToSite.ContainsKey($certHash)) {
            $certToSite[$certHash] = @()
        }
        $certToSite[$certHash] += $siteName
    }
}

# Display the mapping
$certToSite.GetEnumerator() | ForEach-Object {
    $cert = Get-ChildItem -Path Cert:\LocalMachine\My |
            Where-Object { $_.Thumbprint -eq $_.Key }

    [PSCustomObject]@{
        Thumbprint = $_.Key
        Subject = $cert.Subject
        Expiration = $cert.NotAfter
        Sites = $_.Value -join ', '
    }
} | Format-Table -AutoSize
```

## Common Windows Certificate Scenarios

### Scenario 1: Wildcard Certificate

Single wildcard cert (*.example.com) bound to multiple IIS sites:

```
Cert: *.example.com (Thumbprint: ABC123...)
  ├── Site: www.example.com (Binding: *:443:www.example.com)
  ├── Site: api.example.com (Binding: *:443:api.example.com)
  └── Site: shop.example.com (Binding: *:443:shop.example.com)
```

Discovery shows: 1 certificate, 3 bindings

### Scenario 2: SNI (Server Name Indication)

Multiple certificates on same IP:port using SNI:

```
IP: 192.168.1.20:443
  ├── Binding: *:443:www.site1.com → Cert: CN=www.site1.com
  ├── Binding: *:443:www.site2.com → Cert: CN=www.site2.com
  └── Binding: *:443:www.site3.com → Cert: CN=www.site3.com
```

Discovery shows: 3 certificates, 3 bindings (requires IIS 8.0+)

### Scenario 3: Orphaned Certificates

Certificates installed but not bound to any site:

```
LocalMachine\My:
  ├── CN=old-site.example.com [HasPrivateKey=True] ← Not used anywhere
  ├── CN=www.example.com [HasPrivateKey=True] ← Bound to Default Web Site
  └── CN=staging.example.com [HasPrivateKey=True] ← Not used anywhere
```

Discovery identifies these as candidates for removal

## Troubleshooting

### Issue: "IIS bindings not found"

**Cause**: IIS not installed or Web-Server feature disabled

**Solution**:
```powershell
# Check if IIS is installed
Get-WindowsFeature -Name Web-Server

# Install IIS (if needed)
Install-WindowsFeature -Name Web-Server -IncludeManagementTools
```

### Issue: "Cannot import WebAdministration module"

**Cause**: IIS Management Scripts not installed

**Solution**:
```powershell
# Install IIS Management Scripts
Install-WindowsFeature -Name Web-Scripting-Tools

# Import module
Import-Module WebAdministration
```

### Issue: "Access denied reading certificate private key"

**Cause**: Ansible user lacks permissions to LocalMachine\My store

**Solution**:
```powershell
# Grant read access to the Ansible user
$user = "DOMAIN\ansible-svc"
$cert = Get-ChildItem -Path Cert:\LocalMachine\My\$thumbprint
$keyPath = $cert.PrivateKey.CspKeyContainerInfo.UniqueKeyContainerName
$keyFullPath = "C:\ProgramData\Microsoft\Crypto\RSA\MachineKeys\$keyPath"
$acl = Get-Acl -Path $keyFullPath
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $user, "Read", "Allow"
)
$acl.AddAccessRule($rule)
Set-Acl -Path $keyFullPath -AclObject $acl
```

### Issue: "Certificate thumbprint mismatch"

**Cause**: Thumbprint in binding doesn't match any certificate in stores

**Solution**:
```powershell
# Find orphaned bindings
Get-WebBinding | Where-Object { $_.protocol -eq 'https' } | ForEach-Object {
    $certHash = $_.certificateHash
    $storeName = if ($_.certificateStoreName) { $_.certificateStoreName } else { 'My' }
    $cert = Get-ChildItem -Path "Cert:\LocalMachine\$storeName" -ErrorAction SilentlyContinue |
            Where-Object { $_.Thumbprint -eq $certHash }

    if (-not $cert) {
        Write-Warning "Orphaned binding found: $($_.bindingInformation) - Thumbprint: $certHash"
    }
}
```

## Windows Certificate Store Best Practices

### 1. Use Dedicated Service Accounts

Create a dedicated account for certificate management:

```powershell
# Create service account with minimal permissions
New-LocalUser -Name "cert-mgmt-svc" -Description "Certificate Management Service" `
    -NoPassword -UserMayNotChangePassword

# Grant read access to certificate stores only
# (Permissions set via ACLs on individual certificates, as shown above)
```

### 2. Implement Certificate Request Automation

Use ACME protocol with win-acme for Let's Encrypt:

```powershell
# Install win-acme
choco install win-acme

# Configure automatic renewal
wacs.exe --target manual --host www.example.com --installation iis
```

### 3. Monitor Certificate Expiration

Schedule a task to email admins about expiring certificates:

```powershell
# Create monitoring script
$script = @'
$daysWarning = 60
$certs = Get-ChildItem -Path Cert:\LocalMachine\My |
    Where-Object {
        $_.NotAfter -lt (Get-Date).AddDays($daysWarning) -and
        $_.HasPrivateKey
    }

if ($certs) {
    $body = $certs | ConvertTo-Html -Property Subject, NotAfter, Thumbprint
    Send-MailMessage -To "admin@example.com" -From "certs@example.com" `
        -Subject "Certificates Expiring Soon" -Body $body -BodyAsHtml `
        -SmtpServer "smtp.example.com"
}
'@

# Schedule to run daily
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -Command $script"
$trigger = New-ScheduledTaskTrigger -Daily -At 8am
Register-ScheduledTask -TaskName "CertificateExpiryCheck" `
    -Action $action -Trigger $trigger -User "SYSTEM"
```

## Ansible Integration Examples

### Example 1: Daily Certificate Discovery Job

```yaml
# Schedule in AAP/Tower
- name: Daily Windows Certificate Discovery
  hosts: windows_servers
  schedule: "0 2 * * *"  # 2 AM daily

  tasks:
    - name: Run certificate discovery
      include_role:
        name: certificate_discovery
        vars:
          discovery_method: iis_bindings

    - name: Email report if certificates expiring soon
      community.general.mail:
        to: security-team@example.com
        subject: "Windows Certificates Expiring Soon"
        body: "{{ expiring_certs | to_nice_json }}"
      when: expiring_certs | length > 0
```

### Example 2: Pre-Renewal Validation

```yaml
# Verify certificate before renewal
- name: Pre-Renewal Validation
  hosts: windows_servers

  tasks:
    - name: Check if certificate is actually in use
      ansible.windows.win_powershell:
        script: |
          $thumbprint = "{{ cert_thumbprint }}"
          $bindings = Get-WebBinding | Where-Object {
              $_.certificateHash -eq $thumbprint
          }
          $Ansible.Result = @{
              InUse = ($bindings.Count -gt 0)
              Sites = $bindings | ForEach-Object {
                  $_.ItemXPath -replace '.*name=''([^'']+)''.*', '$1'
              }
          }
      register: cert_usage

    - name: Fail if certificate not in use
      fail:
        msg: "Certificate {{ cert_thumbprint }} is not bound to any IIS site"
      when: not cert_usage.result.InUse
```

## See Also

- [Windows IIS Renewal Workflow](../iis_windows/README.md)
- [Certificate Store Management](https://docs.microsoft.com/en-us/windows-server/networking/technologies/certificate-services)
- [IIS SSL Certificate Binding](https://docs.microsoft.com/en-us/iis/manage/configuring-security/how-to-set-up-ssl-on-iis)
