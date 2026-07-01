# Create-SharedDrive.ps1
# Creates a Windows file share with specified permissions
# Parameters can be passed from Ansible

param(
    [Parameter(Mandatory=$true)]
    [string]$ShareName,

    [Parameter(Mandatory=$true)]
    [string]$SharePath,

    [Parameter(Mandatory=$false)]
    [string]$Description = "File share created by Ansible",

    [Parameter(Mandatory=$false)]
    [string[]]$ReadUsers = @(),

    [Parameter(Mandatory=$false)]
    [string[]]$ChangeUsers = @(),

    [Parameter(Mandatory=$false)]
    [string[]]$FullControlUsers = @("Administrators"),

    [Parameter(Mandatory=$false)]
    [switch]$RemoveExisting
)

# Function to write structured output for Ansible
function Write-AnsibleOutput {
    param($Message, $Type = "INFO")
    $output = @{
        timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        type = $Type
        message = $Message
    }
    Write-Output ($output | ConvertTo-Json -Compress)
}

try {
    # Check if share already exists
    $existingShare = Get-SmbShare -Name $ShareName -ErrorAction SilentlyContinue

    if ($existingShare) {
        if ($RemoveExisting) {
            Write-AnsibleOutput "Removing existing share: $ShareName" "INFO"
            Remove-SmbShare -Name $ShareName -Force
        } else {
            Write-AnsibleOutput "Share already exists: $ShareName. Use -RemoveExisting to replace." "ERROR"
            exit 1
        }
    }

    # Create the directory if it doesn't exist
    if (-not (Test-Path $SharePath)) {
        Write-AnsibleOutput "Creating directory: $SharePath" "INFO"
        New-Item -Path $SharePath -ItemType Directory -Force | Out-Null
    }

    # Create the SMB share
    Write-AnsibleOutput "Creating SMB share: $ShareName at $SharePath" "INFO"
    New-SmbShare -Name $ShareName -Path $SharePath -Description $Description -FullAccess "Everyone" | Out-Null

    # Set NTFS permissions
    $acl = Get-Acl $SharePath

    # Remove inherited permissions
    $acl.SetAccessRuleProtection($true, $false)

    # Add Full Control for System and Administrators
    $systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "SYSTEM", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow"
    )
    $acl.AddAccessRule($systemRule)

    $adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "Administrators", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow"
    )
    $acl.AddAccessRule($adminRule)

    # Add Read permissions
    foreach ($user in $ReadUsers) {
        Write-AnsibleOutput "Adding Read permission for: $user" "INFO"
        $readRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $user, "ReadAndExecute", "ContainerInherit,ObjectInherit", "None", "Allow"
        )
        $acl.AddAccessRule($readRule)
    }

    # Add Change permissions
    foreach ($user in $ChangeUsers) {
        Write-AnsibleOutput "Adding Change permission for: $user" "INFO"
        $changeRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $user, "Modify", "ContainerInherit,ObjectInherit", "None", "Allow"
        )
        $acl.AddAccessRule($changeRule)
    }

    # Add Full Control permissions
    foreach ($user in $FullControlUsers) {
        if ($user -ne "Administrators" -and $user -ne "SYSTEM") {
            Write-AnsibleOutput "Adding Full Control permission for: $user" "INFO"
            $fullRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
                $user, "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow"
            )
            $acl.AddAccessRule($fullRule)
        }
    }

    # Apply the ACL
    Set-Acl -Path $SharePath -AclObject $acl

    # Set SMB share permissions
    Revoke-SmbShareAccess -Name $ShareName -AccountName "Everyone" -Force | Out-Null

    foreach ($user in $ReadUsers) {
        Grant-SmbShareAccess -Name $ShareName -AccountName $user -AccessRight Read -Force | Out-Null
    }

    foreach ($user in $ChangeUsers) {
        Grant-SmbShareAccess -Name $ShareName -AccountName $user -AccessRight Change -Force | Out-Null
    }

    foreach ($user in $FullControlUsers) {
        Grant-SmbShareAccess -Name $ShareName -AccountName $user -AccessRight Full -Force | Out-Null
    }

    # Get final share details
    $shareInfo = Get-SmbShare -Name $ShareName
    $sharePermissions = Get-SmbShareAccess -Name $ShareName

    $result = @{
        success = $true
        share_name = $ShareName
        share_path = $SharePath
        description = $Description
        unc_path = "\\$env:COMPUTERNAME\$ShareName"
        permissions = @{
            read = $ReadUsers
            change = $ChangeUsers
            full_control = $FullControlUsers
        }
        share_permissions = $sharePermissions | ForEach-Object {
            @{
                account = $_.AccountName
                access_right = $_.AccessRight
                access_control_type = $_.AccessControlType
            }
        }
    }

    Write-Output ($result | ConvertTo-Json -Depth 5)

} catch {
    $errorResult = @{
        success = $false
        error = $_.Exception.Message
        stack_trace = $_.ScriptStackTrace
    }
    Write-Output ($errorResult | ConvertTo-Json)
    exit 1
}
