param()

Write-Output "Flushing DNS resolver cache..."

try {
    Clear-DnsClientCache
    Write-Output "DNS cache flushed successfully."
} catch {
    Write-Error "Failed to flush DNS cache: $_"
    exit 1
}

Write-Output "`nCurrent DNS cache stats:"
Get-DnsClientCache | Measure-Object | Select-Object -ExpandProperty Count | ForEach-Object {
    Write-Output "  Cached entries: $_"
}

exit 0
