param(
    [Parameter(Mandatory=$true)]
    [string]$service_name
)

$svc = Get-Service -Name $service_name -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Error "Service '$service_name' not found"
    exit 1
}

try {
    Start-Service -Name $service_name -ErrorAction Stop
    $svc.Refresh()
    Write-Output "Service '$service_name' started successfully (status: $($svc.Status))"
    exit 0
} catch {
    Write-Error "Failed to start '$service_name': $_"
    exit 1
}
