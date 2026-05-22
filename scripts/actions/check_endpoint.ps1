param(
    [Parameter(Mandatory=$true)]
    [string]$url
)

Write-Output "Diagnosing endpoint: $url"

# 1. DNS resolution
try {
    $uri = [System.Uri]$url
    $host_name = $uri.Host
    Write-Output "`n--- DNS Resolution ---"
    $dns = Resolve-DnsName -Name $host_name -ErrorAction Stop
    Write-Output "Resolved $host_name to: $($dns | Where-Object { $_.QueryType -eq 'A' } | Select-Object -ExpandProperty IPAddress -First 3)"
} catch {
    Write-Error "DNS resolution failed for ${host_name}: $_"
    exit 1
}

# 2. TCP connectivity
Write-Output "`n--- TCP Connectivity ---"
$port = if ($uri.Port -gt 0) { $uri.Port } elseif ($uri.Scheme -eq 'https') { 443 } else { 80 }
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect($host_name, $port)
    Write-Output "TCP connection to ${host_name}:${port} succeeded"
    $tcp.Close()
} catch {
    Write-Error "TCP connection to ${host_name}:${port} failed: $_"
    exit 1
}

# 3. HTTP request with timing
Write-Output "`n--- HTTP Request ---"
try {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 15 -MaximumRedirection 5
    $sw.Stop()
    Write-Output "Status: $($response.StatusCode) $($response.StatusDescription)"
    Write-Output "Latency: $($sw.ElapsedMilliseconds)ms"
    $contentLen = $response.Headers['Content-Length']
    if (-not $contentLen) { $contentLen = 'N/A' }
    Write-Output "Content-Length: $contentLen"
} catch {
    Write-Error "HTTP request failed: $_"
    exit 1
}

Write-Output "`n--- Diagnosis Complete ---"
Write-Output "Endpoint $url is reachable."
exit 0
