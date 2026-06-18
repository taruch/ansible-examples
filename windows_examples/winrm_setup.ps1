# Enhanced WinRM Setup for Ansible
# Run as Administrator on Windows Server
#
# This script:
# 1. Configures WinRM for Ansible connectivity
# 2. Enables HTTPS listener with self-signed certificate
# 3. Configures authentication methods (NTLM, Negotiate, Basic, CredSSP)
# 4. Opens firewall ports
# 5. Creates ansible service account (optional)
#
# Usage:
#   .\winrm_setup_improved.ps1
#   .\winrm_setup_improved.ps1 -SkipCredSSP
#   .\winrm_setup_improved.ps1 -CreateAnsibleUser -AnsiblePassword "SecureP@ss123"

param(
    [switch]$SkipCredSSP,
    [switch]$CreateAnsibleUser,
    [string]$AnsiblePassword = "PASSW0RD",
    [switch]$SkipNetworkProfile
)

Write-Host "`n=== WinRM Setup for Ansible ===" -ForegroundColor Cyan
Write-Host "Starting configuration...`n" -ForegroundColor Cyan

# Ensure running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    exit 1
}

# Step 1: Disable .NET Optimization (reduces CPU usage)
Write-Host "[1/9] Disabling .NET Optimization tasks..." -ForegroundColor Yellow
try {
    Get-ScheduledTask *ngen* -ErrorAction SilentlyContinue | Disable-ScheduledTask | Out-Null
    Write-Host "  ✓ .NET Optimization disabled" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Could not disable .NET Optimization: $_" -ForegroundColor Yellow
}

# Step 2: Set network profile to Private (required for WinRM)
if (-not $SkipNetworkProfile) {
    Write-Host "`n[2/9] Setting network profile to Private..." -ForegroundColor Yellow
    try {
        Get-NetConnectionProfile | Set-NetConnectionProfile -NetworkCategory Private -ErrorAction Stop
        Write-Host "  ✓ Network profile set to Private" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠ Could not change network profile: $_" -ForegroundColor Yellow
        Write-Host "  ⚠ You may need to do this manually in Network Settings" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n[2/9] Skipping network profile change (use -SkipNetworkProfile flag)" -ForegroundColor Yellow
}

# Step 3: Remove Group Policy restrictions on WinRM
Write-Host "`n[3/9] Removing WinRM Group Policy restrictions..." -ForegroundColor Yellow
$policiesRemoved = 0
$policies = @(
    "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WinRM\Service"
)
foreach ($policy in $policies) {
    if (Test-Path $policy) {
        try {
            Remove-Item -Path $policy -Recurse -Force -ErrorAction Stop
            $policiesRemoved++
        } catch {
            Write-Host "  ⚠ Could not remove policy $policy" -ForegroundColor Yellow
        }
    }
}
Write-Host "  ✓ Removed $policiesRemoved policy restrictions" -ForegroundColor Green

# Step 4: Download and run Ansible's WinRM configuration script
Write-Host "`n[4/9] Downloading Ansible WinRM configuration script..." -ForegroundColor Yellow
$url = "https://raw.githubusercontent.com/ansible/ansible/devel/examples/scripts/ConfigureRemotingForAnsible.ps1"
$output = "$env:TEMP\ConfigureRemotingForAnsible.ps1"

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $url -OutFile $output -ErrorAction Stop
    Write-Host "  ✓ Downloaded configuration script" -ForegroundColor Green

    # Run the script
    Write-Host "`n[5/9] Running WinRM configuration..." -ForegroundColor Yellow
    if ($SkipCredSSP) {
        & $output -ForceNewSSLCert
        Write-Host "  ✓ WinRM configured (CredSSP disabled)" -ForegroundColor Green
    } else {
        & $output -ForceNewSSLCert -EnableCredSSP
        Write-Host "  ✓ WinRM configured with CredSSP" -ForegroundColor Green
    }
} catch {
    Write-Host "  ✗ Failed to download/run configuration script: $_" -ForegroundColor Red
    Write-Host "  ℹ Continuing with manual configuration..." -ForegroundColor Yellow

    # Manual WinRM configuration fallback
    Write-Host "`n[5/9] Performing manual WinRM configuration..." -ForegroundColor Yellow

    # Enable WinRM
    Enable-PSRemoting -Force -SkipNetworkProfileCheck

    # Configure HTTPS listener
    $hostname = $env:COMPUTERNAME
    $cert = New-SelfSignedCertificate -DnsName $hostname -CertStoreLocation Cert:\LocalMachine\My
    New-Item -Path WSMan:\localhost\Listener -Transport HTTPS -Address * -CertificateThumbPrint $cert.Thumbprint -Force

    # Enable Basic authentication
    Set-Item -Path WSMan:\localhost\Service\Auth\Basic -Value $true

    Write-Host "  ✓ Manual WinRM configuration completed" -ForegroundColor Green
}

# Step 6: Configure authentication methods
Write-Host "`n[6/9] Configuring authentication methods..." -ForegroundColor Yellow
try {
    Set-Item WSMan:\localhost\Service\Auth\Basic -Value $true -Force
    Set-Item WSMan:\localhost\Service\Auth\Negotiate -Value $true -Force

    if (-not $SkipCredSSP) {
        # Enable CredSSP server
        Enable-WSManCredSSP -Role Server -Force | Out-Null
    }

    Write-Host "  ✓ Authentication methods configured" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Some authentication settings could not be changed: $_" -ForegroundColor Yellow
}

# Step 7: Increase WinRM limits
Write-Host "`n[7/9] Increasing WinRM resource limits..." -ForegroundColor Yellow
try {
    Set-Item WSMan:\localhost\Shell\MaxMemoryPerShellMB 1024 -Force
    Set-Item WSMan:\localhost\Plugin\microsoft.powershell\Quotas\MaxMemoryPerShellMB 1024 -Force
    Set-Item WSMan:\localhost\MaxTimeoutms 1800000 -Force
    Set-Item WSMan:\localhost\Service\MaxConcurrentOperationsPerUser 4294967295 -Force
    Write-Host "  ✓ Resource limits increased" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Could not increase all limits: $_" -ForegroundColor Yellow
}

# Step 8: Configure firewall
Write-Host "`n[8/9] Configuring Windows Firewall..." -ForegroundColor Yellow
try {
    # Enable existing rules
    Enable-NetFirewallRule -DisplayName "Windows Remote Management (HTTP-In)" -ErrorAction SilentlyContinue
    Enable-NetFirewallRule -DisplayName "Windows Remote Management (HTTPS-In)" -ErrorAction SilentlyContinue

    # Create custom rules if they don't exist
    $httpRule = Get-NetFirewallRule -Name "WinRM-HTTP-Ansible" -ErrorAction SilentlyContinue
    if (-not $httpRule) {
        New-NetFirewallRule -Name "WinRM-HTTP-Ansible" -DisplayName "WinRM HTTP (Ansible)" `
            -Protocol TCP -LocalPort 5985 -Action Allow -Enabled True | Out-Null
    }

    $httpsRule = Get-NetFirewallRule -Name "WinRM-HTTPS-Ansible" -ErrorAction SilentlyContinue
    if (-not $httpsRule) {
        New-NetFirewallRule -Name "WinRM-HTTPS-Ansible" -DisplayName "WinRM HTTPS (Ansible)" `
            -Protocol TCP -LocalPort 5986 -Action Allow -Enabled True | Out-Null
    }

    Write-Host "  ✓ Firewall configured for WinRM" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Could not configure firewall: $_" -ForegroundColor Yellow
}

# Step 9: Create Ansible service account (optional)
if ($CreateAnsibleUser) {
    Write-Host "`n[9/9] Creating ansible service account..." -ForegroundColor Yellow
    try {
        $SecurePassword = ConvertTo-SecureString $AnsiblePassword -AsPlainText -Force

        # Check if user already exists
        $userExists = Get-LocalUser -Name "ansible" -ErrorAction SilentlyContinue

        if ($userExists) {
            Write-Host "  ℹ User 'ansible' already exists, updating password..." -ForegroundColor Yellow
            $userExists | Set-LocalUser -Password $SecurePassword
        } else {
            New-LocalUser -Name "ansible" -Description "Ansible Service Account" -Password $SecurePassword -PasswordNeverExpires | Out-Null
            Write-Host "  ✓ Created user 'ansible'" -ForegroundColor Green
        }

        # Add to Administrators group
        try {
            Add-LocalGroupMember -Group "Administrators" -Member "ansible" -ErrorAction Stop
            Write-Host "  ✓ Added 'ansible' to Administrators group" -ForegroundColor Green
        } catch {
            if ($_.Exception.Message -like "*already a member*") {
                Write-Host "  ℹ User 'ansible' already in Administrators group" -ForegroundColor Yellow
            } else {
                throw $_
            }
        }

        Write-Host "  ✓ Ansible service account configured" -ForegroundColor Green
        Write-Host "  ℹ Username: ansible" -ForegroundColor Cyan
        Write-Host "  ℹ Password: $AnsiblePassword" -ForegroundColor Cyan
    } catch {
        Write-Host "  ✗ Could not create ansible user: $_" -ForegroundColor Red
    }
} else {
    Write-Host "`n[9/9] Skipping ansible user creation (use -CreateAnsibleUser flag)" -ForegroundColor Yellow
}

# Restart WinRM service
Write-Host "`n=== Restarting WinRM Service ===" -ForegroundColor Cyan
Restart-Service WinRM
Write-Host "  ✓ WinRM service restarted" -ForegroundColor Green

# Display configuration summary
Write-Host "`n=== Configuration Summary ===" -ForegroundColor Cyan

Write-Host "`nWinRM Service Status:" -ForegroundColor Yellow
Get-Service WinRM | Format-Table -AutoSize

Write-Host "Authentication Methods:" -ForegroundColor Yellow
$auth = Get-Item WSMan:\localhost\Service\Auth\* | Select-Object Name, Value
$auth | Format-Table -AutoSize

Write-Host "WinRM Listeners:" -ForegroundColor Yellow
try {
    $listeners = Get-ChildItem WSMan:\localhost\Listener
    foreach ($listener in $listeners) {
        $config = Get-ChildItem "WSMan:\localhost\Listener\$($listener.Name)"
        Write-Host "  Listener: $($listener.Name)"
        $config | Where-Object { $_.Name -in @('Address', 'Transport', 'Port') } | ForEach-Object {
            Write-Host "    $($_.Name): $($_.Value)"
        }
    }
} catch {
    Write-Host "  ⚠ Could not retrieve listener details" -ForegroundColor Yellow
}

if (-not $SkipCredSSP) {
    Write-Host "`nCredSSP Status:" -ForegroundColor Yellow
    try {
        Get-WSManCredSSP
    } catch {
        Write-Host "  CredSSP not configured" -ForegroundColor Yellow
    }
}

Write-Host "`nFirewall Rules:" -ForegroundColor Yellow
Get-NetFirewallRule -DisplayName "*WinRM*" | Where-Object { $_.Enabled -eq $true } |
    Select-Object DisplayName, Enabled, Direction, Action | Format-Table -AutoSize

# Connection test instructions
Write-Host "`n=== Testing Connection ===" -ForegroundColor Cyan
Write-Host "From your Ansible controller, test with:" -ForegroundColor Yellow
Write-Host "  ansible windows -i hosts -m win_ping" -ForegroundColor White
Write-Host ""
Write-Host "Or create an inventory file (hosts):" -ForegroundColor Yellow
Write-Host "[windows]" -ForegroundColor White
Write-Host "$env:COMPUTERNAME" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "[windows:vars]" -ForegroundColor White
if ($CreateAnsibleUser) {
    Write-Host "ansible_user=ansible" -ForegroundColor White
    Write-Host "ansible_password=$AnsiblePassword" -ForegroundColor White
} else {
    Write-Host "ansible_user=Administrator" -ForegroundColor White
    Write-Host "ansible_password=YourPasswordHere" -ForegroundColor White
}
Write-Host "ansible_connection=winrm" -ForegroundColor White
Write-Host "ansible_winrm_transport=ntlm" -ForegroundColor White
Write-Host "ansible_winrm_server_cert_validation=ignore" -ForegroundColor White
Write-Host "ansible_winrm_port=5986" -ForegroundColor White
Write-Host "ansible_winrm_scheme=https" -ForegroundColor White

Write-Host "`n=== Setup Complete! ===" -ForegroundColor Green
Write-Host "WinRM is now configured for Ansible connectivity" -ForegroundColor Green
Write-Host ""

# Optional: Prompt for computer rename
$rename = Read-Host "Do you want to rename this computer and restart? (y/N)"
if ($rename -eq 'y' -or $rename -eq 'Y') {
    $newName = Read-Host "Enter new computer name"
    if ($newName) {
        Write-Host "Renaming computer to '$newName' and restarting..." -ForegroundColor Yellow
        Rename-Computer -NewName $newName -Force -Restart
    }
} else {
    Write-Host "Skipping computer rename. Setup complete!" -ForegroundColor Green
}
