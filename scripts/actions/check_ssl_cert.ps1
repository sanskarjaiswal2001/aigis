param(
    [Parameter(Mandatory=$true)]
    [string]$domain
)

Write-Output "Checking SSL certificate for: $domain"

# Parse optional port
$port = 443
if ($domain -match '^(.+):(\d+)$') {
    $domain = $Matches[1]
    $port = [int]$Matches[2]
}

# 1. Fetch certificate
Write-Output "`n--- Certificate Details ---"
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect($domain, $port)
    $ssl = New-Object System.Net.Security.SslStream($tcp.GetStream(), $false, { $true })
    $ssl.AuthenticateAsClient($domain)
    $cert = $ssl.RemoteCertificate
    $cert2 = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($cert)

    Write-Output "Subject:    $($cert2.Subject)"
    Write-Output "Issuer:     $($cert2.Issuer)"
    Write-Output "Not Before: $($cert2.NotBefore.ToString('yyyy-MM-dd HH:mm:ss UTC'))"
    Write-Output "Not After:  $($cert2.NotAfter.ToString('yyyy-MM-dd HH:mm:ss UTC'))"

    $daysRemaining = ($cert2.NotAfter - (Get-Date)).Days
    Write-Output "Days Left:  $daysRemaining"

    if ($daysRemaining -le 0) {
        Write-Output "`nSTATUS: EXPIRED"
        Write-Output "`n--- Recommended Steps ---"
        Write-Output "1. Renew the certificate immediately"
        Write-Output "2. If using Let's Encrypt: certbot renew --force-renewal -d $domain"
        Write-Output "3. Restart the web server after renewal"
        Write-Output "4. Verify with: openssl s_client -connect ${domain}:${port}"
        exit 1
    } elseif ($daysRemaining -le 7) {
        Write-Output "`nSTATUS: CRITICAL - Expiring within 7 days"
        Write-Output "`n--- Recommended Steps ---"
        Write-Output "1. Renew the certificate before expiry"
        Write-Output "2. If using Let's Encrypt: certbot renew -d $domain"
        Write-Output "3. Check auto-renewal cron/timer is active"
        exit 1
    } elseif ($daysRemaining -le 30) {
        Write-Output "`nSTATUS: WARNING - Expiring within 30 days"
        Write-Output "`n--- Recommended Steps ---"
        Write-Output "1. Plan certificate renewal"
        Write-Output "2. Verify auto-renewal is configured"
        exit 0
    } else {
        Write-Output "`nSTATUS: OK"
    }

    # 2. Certificate chain
    Write-Output "`n--- Certificate Chain ---"
    $chain = New-Object System.Security.Cryptography.X509Certificates.X509Chain
    $chain.Build($cert2) | Out-Null
    foreach ($element in $chain.ChainElements) {
        Write-Output "  $($element.Certificate.Subject)"
    }

    $ssl.Close()
    $tcp.Close()
    exit 0
} catch {
    Write-Error "SSL check failed: $_"
    Write-Output "`n--- Recommended Steps ---"
    Write-Output "1. Verify the domain DNS resolves correctly"
    Write-Output "2. Check if the server is running and accepting TLS connections"
    Write-Output "3. Test manually: openssl s_client -connect ${domain}:${port} -servername $domain"
    exit 1
}
