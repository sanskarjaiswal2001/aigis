#!/bin/bash
# Check SSL certificate details and expiry for a domain.
# Usage: check_ssl_cert.sh <domain>
set -euo pipefail

DOMAIN="${1:?Usage: check_ssl_cert.sh <domain>}"

# Parse optional port
PORT=443
if echo "$DOMAIN" | grep -q ':'; then
    PORT=$(echo "$DOMAIN" | cut -d: -f2)
    DOMAIN=$(echo "$DOMAIN" | cut -d: -f1)
fi

echo "Checking SSL certificate for: ${DOMAIN}:${PORT}"

# 1. Fetch certificate details
echo -e "\n--- Certificate Details ---"
CERT_INFO=$(echo | openssl s_client -servername "$DOMAIN" -connect "${DOMAIN}:${PORT}" 2>/dev/null)

if [ -z "$CERT_INFO" ]; then
    echo "ERROR: Could not connect to ${DOMAIN}:${PORT}" >&2
    echo -e "\n--- Recommended Steps ---"
    echo "1. Verify DNS resolves: dig $DOMAIN"
    echo "2. Check server is listening on port $PORT"
    echo "3. Check firewall rules"
    exit 1
fi

# Parse dates and subject
SUBJECT=$(echo "$CERT_INFO" | openssl x509 -noout -subject 2>/dev/null | sed 's/subject=//')
ISSUER=$(echo "$CERT_INFO" | openssl x509 -noout -issuer 2>/dev/null | sed 's/issuer=//')
NOT_AFTER=$(echo "$CERT_INFO" | openssl x509 -noout -enddate 2>/dev/null | sed 's/notAfter=//')
NOT_BEFORE=$(echo "$CERT_INFO" | openssl x509 -noout -startdate 2>/dev/null | sed 's/notBefore=//')

echo "Subject:    $SUBJECT"
echo "Issuer:     $ISSUER"
echo "Not Before: $NOT_BEFORE"
echo "Not After:  $NOT_AFTER"

# Calculate days remaining
EXPIRY_EPOCH=$(date -d "$NOT_AFTER" +%s 2>/dev/null || date -jf "%b %d %T %Y %Z" "$NOT_AFTER" +%s 2>/dev/null)
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))
echo "Days Left:  $DAYS_LEFT"

# 2. Certificate chain
echo -e "\n--- Certificate Chain ---"
echo "$CERT_INFO" | grep -E "^ [0-9]+ s:" | head -5 || echo "(chain info not available)"

# 3. Status and recommendations
if [ "$DAYS_LEFT" -le 0 ]; then
    echo -e "\nSTATUS: EXPIRED"
    echo -e "\n--- Recommended Steps ---"
    echo "1. Renew the certificate immediately"
    echo "2. If Let's Encrypt: sudo certbot renew --force-renewal -d $DOMAIN"
    echo "3. Restart web server: sudo systemctl restart nginx  # or apache2"
    echo "4. Verify: openssl s_client -connect ${DOMAIN}:${PORT} -servername $DOMAIN"
    exit 1
elif [ "$DAYS_LEFT" -le 7 ]; then
    echo -e "\nSTATUS: CRITICAL - Expiring within 7 days"
    echo -e "\n--- Recommended Steps ---"
    echo "1. Renew the certificate: sudo certbot renew -d $DOMAIN"
    echo "2. Check auto-renewal: sudo systemctl status certbot.timer"
    echo "3. Restart web server after renewal"
    exit 1
elif [ "$DAYS_LEFT" -le 30 ]; then
    echo -e "\nSTATUS: WARNING - Expiring within 30 days"
    echo -e "\n--- Recommended Steps ---"
    echo "1. Plan certificate renewal"
    echo "2. Verify auto-renewal: sudo certbot renew --dry-run"
    exit 0
else
    echo -e "\nSTATUS: OK"
    exit 0
fi
