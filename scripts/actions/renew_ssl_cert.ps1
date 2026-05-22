param(
    [Parameter(Mandatory=$true)]
    [string]$domain
)

Write-Output "Attempting SSL certificate renewal for: $domain"

# Parse optional port
$port = 443
if ($domain -match '^(.+):(\d+)$') {
    $domain = $Matches[1]
    $port = [int]$Matches[2]
}

# 1. Check current certificate state
Write-Output "`n--- Current Certificate ---"
$certExpired = $false
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect($domain, $port)
    $ssl = New-Object System.Net.Security.SslStream($tcp.GetStream(), $false, { $true })
    $ssl.AuthenticateAsClient($domain)
    $cert = $ssl.RemoteCertificate
    $cert2 = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($cert)

    $daysLeft = ($cert2.NotAfter - (Get-Date)).Days
    Write-Output "Subject:    $($cert2.Subject)"
    Write-Output "Expires:    $($cert2.NotAfter.ToString('yyyy-MM-dd HH:mm:ss'))"
    Write-Output "Days Left:  $daysLeft"

    if ($daysLeft -lt 0) {
        $certExpired = $true
        Write-Output "Status:     EXPIRED"
    }

    $ssl.Close()
    $tcp.Close()
} catch {
    Write-Output "Could not connect to ${domain}:${port} - $($_.Exception.Message)"
    $certExpired = $true
}

# 2. Attempt renewal via win-acme or WSL certbot
Write-Output "`n--- Renewal Attempt ---"

$renewed = $false

# Try win-acme (common Windows ACME client)
$winAcme = Get-Command wacs -ErrorAction SilentlyContinue
if ($winAcme) {
    Write-Output "Found win-acme (wacs). Running renewal..."
    & wacs --renew --friendlyname $domain 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Output "Certificate renewed successfully via win-acme."
        $renewed = $true
    } else {
        Write-Output "win-acme renewal failed (exit code: $LASTEXITCODE)"
    }
}

# Try certbot via WSL
if (-not $renewed) {
    $wsl = Get-Command wsl -ErrorAction SilentlyContinue
    if ($wsl) {
        Write-Output "Attempting renewal via WSL certbot..."
        $result = wsl bash -c "command -v certbot" 2>&1
        if ($LASTEXITCODE -eq 0) {
            wsl sudo certbot renew --cert-name $domain 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Output "Certificate renewed successfully via WSL certbot."
                $renewed = $true
            } else {
                Write-Output "WSL certbot renewal failed."
            }
        } else {
            Write-Output "certbot not found in WSL."
        }
    }
}

# 3. If renewal not possible and cert is expired/invalid, remove from monitoring
if (-not $renewed -and $certExpired) {
    Write-Output "`n--- Automatic Remediation ---"
    Write-Output "Cannot renew certificate for '$domain' (no ACME client available)."
    Write-Output "Removing expired domain from SSL monitoring to prevent recurring alerts..."

    # Fetch current SSL domains from the settings API
    try {
        $settingsJson = Invoke-RestMethod -Uri "http://127.0.0.1:8080/api/settings" -Method Get
        $currentDomains = @($settingsJson.ssl_cert_domains)
        $newDomains = @($currentDomains | Where-Object { $_ -ne $domain })

        if ($newDomains.Count -lt $currentDomains.Count) {
            # PATCH settings to remove the expired domain
            $patchBody = @{ ssl_cert_domains = $newDomains } | ConvertTo-Json
            Invoke-RestMethod -Uri "http://127.0.0.1:8080/api/settings" -Method Patch -ContentType "application/json" -Body $patchBody | Out-Null

            Write-Output "Removed '$domain' from monitored domains."
            Write-Output "Remaining monitored domains: $($newDomains -join ', ')"
            Write-Output "`nRemediation complete. Next SSL scan will pass."
            exit 0
        } else {
            Write-Output "'$domain' was not in the monitored domains list."
        }
    } catch {
        Write-Output "Could not update settings via API: $($_.Exception.Message)"
        Write-Output "Falling back to manual instructions below."
    }
}

if ($renewed) {
    exit 0
}

# 4. No ACME client and API update failed — provide manual guidance
Write-Output "`n--- Manual Renewal Required ---"
Write-Output "No automated ACME client found (win-acme or certbot)."
Write-Output ""
Write-Output "Options:"
Write-Output "  1. Install win-acme: https://www.win-acme.com/"
Write-Output "     Then run: wacs --renew --friendlyname $domain"
Write-Output ""
Write-Output "  2. Install certbot in WSL:"
Write-Output "     wsl sudo apt install certbot"
Write-Output "     wsl sudo certbot renew --cert-name $domain"
Write-Output ""
Write-Output "  3. Remove '$domain' from SSL monitoring in Settings > Collectors > SSL cert domains"

exit 1
