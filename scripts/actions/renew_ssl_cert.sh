#!/bin/bash
# Attempt to renew an SSL certificate via certbot.
# Usage: renew_ssl_cert.sh <domain>
set -euo pipefail

DOMAIN="${1:?Usage: renew_ssl_cert.sh <domain>}"

echo "Attempting SSL certificate renewal for: $DOMAIN"

# Check certbot is available
if ! command -v certbot &>/dev/null; then
    echo "ERROR: certbot not found. Install it first:" >&2
    echo "  sudo apt install certbot  # Debian/Ubuntu" >&2
    echo "  sudo dnf install certbot  # Fedora/RHEL" >&2
    exit 1
fi

# Dry-run first
echo -e "\n--- Dry Run ---"
if sudo certbot renew --cert-name "$DOMAIN" --dry-run 2>&1; then
    echo "Dry run succeeded"
else
    echo "Dry run failed — check certbot configuration" >&2
    exit 1
fi

# Actual renewal
echo -e "\n--- Renewing Certificate ---"
sudo certbot renew --cert-name "$DOMAIN" 2>&1

# Restart common web servers if running
echo -e "\n--- Restarting Web Server ---"
if systemctl is-active --quiet nginx; then
    sudo systemctl reload nginx
    echo "Reloaded nginx"
elif systemctl is-active --quiet apache2; then
    sudo systemctl reload apache2
    echo "Reloaded apache2"
elif systemctl is-active --quiet httpd; then
    sudo systemctl reload httpd
    echo "Reloaded httpd"
else
    echo "No common web server detected — restart manually if needed"
fi

# Verify
echo -e "\n--- Verification ---"
echo | openssl s_client -servername "$DOMAIN" -connect "${DOMAIN}:443" 2>/dev/null | openssl x509 -noout -dates
echo "Certificate renewal complete."
exit 0
