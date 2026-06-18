# WinRM Authentication Troubleshooting Guide

## Understanding the Error

```
credssp: The server did not response CredSSP being an available authentication method
actual: 'Negotiate, Basic realm="WSMAN"'
```

This error means:
- Your Ansible playbook is configured to use **CredSSP** authentication
- The Windows server is only offering **Negotiate** and **Basic** authentication
- CredSSP is either not enabled or not configured properly on the Windows host

## Quick Fix: Use NTLM Instead

The easiest solution is to change your playbook's authentication method from `credssp` to `ntlm`.

### Update Your Playbook

Change this:
```yaml
vars:
  ansible_connection: winrm
  ansible_winrm_transport: credssp  # ← Change this
  ansible_winrm_server_cert_validation: ignore
  ansible_winrm_port: 5986
  ansible_winrm_scheme: https
```

To this:
```yaml
vars:
  ansible_connection: winrm
  ansible_winrm_transport: ntlm  # ← Use NTLM
  ansible_winrm_server_cert_validation: ignore
  ansible_winrm_port: 5986
  ansible_winrm_scheme: https
```

### Test Connection

```bash
ansible windows -i hosts -m win_ping
```

Expected output:
```json
hostname | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

## WinRM Authentication Methods Explained

| Method | Use Case | Pros | Cons | Encryption |
|--------|----------|------|------|------------|
| **NTLM** | Most common, domain or local auth | Simple, works everywhere | Hash-based | Yes (over HTTPS) |
| **Kerberos** | Domain environments | Most secure, mutual auth | Requires AD, complex setup | Yes |
| **CredSSP** | Double-hop scenarios | Enables credential delegation | Security risks, complex | Yes |
| **Basic** | Testing only | Simple | Credentials in clear text | Only over HTTPS |
| **Certificate** | Non-interactive, automation | Very secure | Certificate management | Yes |

### When to Use Each

**Use NTLM when:**
- ✅ Connecting to standalone Windows servers
- ✅ Using local administrator accounts
- ✅ Not delegating credentials to other servers
- ✅ Simple, straightforward authentication needed

**Use Kerberos when:**
- ✅ In an Active Directory domain
- ✅ Need mutual authentication
- ✅ Highest security required
- ✅ Using domain accounts

**Use CredSSP when:**
- ⚠️ Need to delegate credentials (double-hop)
- ⚠️ Accessing network resources from remote session
- ⚠️ Example: Remote PowerShell needs to connect to SQL Server on another host
- ❌ **Security warning**: Exposes credentials to potential theft

**Use Basic when:**
- ❌ Testing only, never production
- ❌ Over HTTPS only (credentials sent encoded but not encrypted)

## Enable CredSSP (If You Really Need It)

### On Windows Server

Run as Administrator:

```powershell
# Enable CredSSP server role
Enable-WSManCredSSP -Role Server -Force

# Verify
Get-WSManCredSSP
```

Expected output:
```
The machine is configured to allow delegating fresh credentials to the following target(s): wsman/*
This computer is configured to receive credentials from a remote client computer.
```

### On Ansible Controller

Install required package:

```bash
# RHEL/CentOS/Rocky
sudo dnf install -y python3-requests-credssp

# Ubuntu/Debian
sudo apt-get install -y python3-requests-credssp

# Or via pip
pip3 install pywinrm[credssp]
```

### Test CredSSP Connection

```bash
ansible windows -i hosts -m win_ping -e "ansible_winrm_transport=credssp"
```

## Verify WinRM Configuration on Windows

### Check WinRM Service

```powershell
# Check service status
Get-Service WinRM

# Should show: Running
```

### Check WinRM Configuration

```powershell
# View full WinRM configuration
winrm get winrm/config

# Check authentication methods
winrm get winrm/config/service/auth
```

Expected output for auth:
```
Auth
    Basic = true
    Kerberos = true
    Negotiate = true
    Certificate = false
    CredSSP = true          # Should be true if enabled
    CbtHardeningLevel = Relaxed
```

### Check Listeners

```powershell
# List WinRM listeners
winrm enumerate winrm/config/listener

# Should show both HTTP (5985) and HTTPS (5986) listeners
```

### Check Allowed Hosts

```powershell
# Check trusted hosts (for non-domain scenarios)
Get-Item WSMan:\localhost\Client\TrustedHosts

# Set to allow all (testing only)
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
```

## Enhanced WinRM Setup Script

Here's an improved version of your setup script with better CredSSP configuration:

```powershell
# Enhanced WinRM Setup for Ansible
# Run as Administrator

# Disable .Net Optimization Service
Get-ScheduledTask *ngen* | Disable-ScheduledTask

# Remove WinRM policies
reg delete "HKLM\SOFTWARE\Policies\Microsoft\Windows\WinRM\Service" /v AllowBasic /f 2>$null
reg delete "HKLM\SOFTWARE\Policies\Microsoft\Windows\WinRM\Service" /v AllowUnencryptedTraffic /f 2>$null
reg delete "HKLM\SOFTWARE\Policies\Microsoft\Windows\WinRM\Service" /v DisableRunAs /f 2>$null

# Download and run Ansible's WinRM configuration script
$url = "https://raw.githubusercontent.com/ansible/ansible/devel/examples/scripts/ConfigureRemotingForAnsible.ps1"
$output = "$env:TEMP\ConfigureRemotingForAnsible.ps1"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $url -OutFile $output

# Run with options
& $output -ForceNewSSLCert -EnableCredSSP

# Additional CredSSP configuration
Enable-WSManCredSSP -Role Server -Force

# Increase memory limit for WinRM
Set-Item WSMan:\localhost\Shell\MaxMemoryPerShellMB 1024

# Increase timeout
Set-Item WSMan:\localhost\MaxTimeoutms 1800000

# Allow unencrypted traffic (only if using HTTP - not recommended)
# Set-Item WSMan:\localhost\Service\AllowUnencrypted $true

# Restart WinRM service
Restart-Service WinRM

# Verify configuration
Write-Host "`n=== WinRM Configuration ===" -ForegroundColor Green
winrm get winrm/config/service/auth

Write-Host "`n=== WinRM Listeners ===" -ForegroundColor Green
winrm enumerate winrm/config/listener

Write-Host "`n=== CredSSP Status ===" -ForegroundColor Green
Get-WSManCredSSP

Write-Host "`nWinRM setup complete!" -ForegroundColor Green
```

## Test WinRM from Ansible

### Method 1: ansible ad-hoc command

```bash
ansible windows -i hosts -m win_ping -vvv
```

The `-vvv` shows detailed connection information.

### Method 2: Test playbook

Create `test_winrm.yml`:

```yaml
---
- name: Test WinRM connectivity and authentication
  hosts: windows
  gather_facts: false
  
  vars:
    ansible_connection: winrm
    ansible_winrm_transport: ntlm
    ansible_winrm_server_cert_validation: ignore
    ansible_winrm_port: 5986
    ansible_winrm_scheme: https
  
  tasks:
    - name: Ping test
      ansible.windows.win_ping:
      
    - name: Get hostname
      ansible.windows.win_shell: hostname
      register: hostname_result
      
    - name: Display hostname
      ansible.builtin.debug:
        var: hostname_result.stdout
        
    - name: Check authentication method
      ansible.windows.win_shell: |
        $session = Get-WSManInstance -ResourceURI winrm/config/service
        [PSCustomObject]@{
          AllowUnencrypted = $session.AllowUnencrypted
          Auth_Basic = $session.Auth_Basic
          Auth_Kerberos = $session.Auth_Kerberos
          Auth_Negotiate = $session.Auth_Negotiate
          Auth_CredSSP = $session.Auth_CredSSP
        } | Format-List
      register: auth_check
      
    - name: Display auth methods
      ansible.builtin.debug:
        var: auth_check.stdout_lines
```

Run:
```bash
ansible-playbook test_winrm.yml
```

## Common WinRM Errors and Solutions

### Error: "Connection timeout"

```
msg: "HTTPSConnectionPool(host='server', port=5986): Max retries exceeded"
```

**Causes:**
- Firewall blocking port 5986
- WinRM service not running
- Wrong port number

**Solutions:**
```powershell
# Check firewall
Get-NetFirewallRule -DisplayName "*WinRM*"

# Enable firewall rule
Enable-NetFirewallRule -DisplayName "Windows Remote Management (HTTPS-In)"

# Or create new rule
New-NetFirewallRule -Name "WinRM-HTTPS" -DisplayName "WinRM HTTPS" `
  -Protocol TCP -LocalPort 5986 -Action Allow -Enabled True
```

### Error: "Bad HTTP response"

```
msg: "Bad HTTP response returned from server. Code 500"
```

**Causes:**
- Authentication failure
- Wrong credentials
- Account not in Administrators group

**Solutions:**
```powershell
# Verify user is admin
net localgroup administrators

# Add user to administrators
net localgroup administrators ec2-user /add
```

### Error: "Kerberos auth failed"

```
msg: "Kerberos auth failed: kinit command failed"
```

**Solution:**
Use NTLM instead unless you're in a domain:
```yaml
ansible_winrm_transport: ntlm
```

### Error: "Certificate verification failed"

```
msg: "certificate verify failed: self signed certificate"
```

**Solution:**
Disable certificate validation (non-production):
```yaml
ansible_winrm_server_cert_validation: ignore
```

## Inventory File Examples

### Using NTLM (Recommended for EC2)

```ini
[windows]
ec2-18-188-53-16.us-east-2.compute.amazonaws.com

[windows:vars]
ansible_user=Administrator
ansible_password=YourPassword
ansible_connection=winrm
ansible_winrm_transport=ntlm
ansible_winrm_server_cert_validation=ignore
ansible_winrm_port=5986
ansible_winrm_scheme=https
```

### Using CredSSP (Advanced)

```ini
[windows]
win-server.example.com

[windows:vars]
ansible_user=Administrator
ansible_password=YourPassword
ansible_connection=winrm
ansible_winrm_transport=credssp
ansible_winrm_server_cert_validation=ignore
ansible_winrm_port=5986
ansible_winrm_scheme=https
```

### Using Kerberos (Domain)

```ini
[windows]
server.domain.local

[windows:vars]
ansible_user=domain\admin
ansible_password=YourPassword
ansible_connection=winrm
ansible_winrm_transport=kerberos
ansible_port=5986
```

## Security Best Practices

1. **Use HTTPS (port 5986), not HTTP (port 5985)**
   - HTTP sends data in clear text
   - HTTPS encrypts the connection

2. **Avoid CredSSP unless absolutely necessary**
   - Exposes credentials to potential theft
   - Use only for double-hop scenarios
   - Disable after use

3. **Use strong passwords**
   - Minimum 12 characters
   - Mix of upper/lower case, numbers, symbols

4. **Limit WinRM access**
   - Restrict firewall to specific IP ranges
   - Use Windows Firewall advanced rules

5. **Use service accounts**
   - Don't use Administrator directly
   - Create dedicated ansible service account
   - Grant minimum necessary privileges

6. **Rotate credentials regularly**
   - Use Ansible Vault or AAP credentials
   - Don't hardcode passwords in playbooks

## Debugging Tips

### Enable WinRM Logging

```powershell
# Enable WinRM event logging
wevtutil set-log Microsoft-Windows-WinRM/Operational /enabled:true

# View logs
Get-WinEvent -LogName Microsoft-Windows-WinRM/Operational -MaxEvents 20 | Format-List
```

### Test from Windows Client

```powershell
# Test WinRM from another Windows machine
Test-WSMan -ComputerName server.example.com -Port 5986 -UseSSL

# Enter remote session (CredSSP test)
Enter-PSSession -ComputerName server.example.com -Credential (Get-Credential) `
  -Authentication Credssp -UseSSL
```

### Check from Linux

```bash
# Test HTTPS port
nc -zv server.example.com 5986

# Test with curl
curl -k https://server.example.com:5986/wsman

# Should return XML with WinRM version info
```

## Summary: Recommended Approach

For most Ansible automation against Windows:

1. **Use NTLM authentication** (simplest, most reliable)
2. **Use HTTPS (port 5986)** (encrypted)
3. **Disable certificate validation** (if using self-signed certs)
4. **Only use CredSSP if you need credential delegation**

Example inventory:
```yaml
all:
  children:
    windows:
      hosts:
        win-server-01:
          ansible_host: 10.0.1.100
      vars:
        ansible_user: ansible_svc
        ansible_password: "{{ vault_windows_password }}"
        ansible_connection: winrm
        ansible_winrm_transport: ntlm
        ansible_winrm_server_cert_validation: ignore
        ansible_winrm_port: 5986
        ansible_winrm_scheme: https
```

This configuration works in 95% of scenarios and avoids the complexity and security risks of CredSSP.
