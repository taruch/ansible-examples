param(
    [string]$OutputPath = ""
)

$hostname  = $env:COMPUTERNAME
$os        = (Get-WmiObject Win32_OperatingSystem).Caption
$location  = Get-Location

Write-Output "Report from  : $hostname"
Write-Output "OS           : $os"
Write-Output "Location     : $location"

if ($OutputPath) {
    Write-Output "Output path  : $OutputPath"
}
