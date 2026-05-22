#!/bin/bash
# Diagnose HTTP endpoint connectivity issues.
# Usage: check_endpoint.sh <url>
set -euo pipefail

URL="${1:?Usage: check_endpoint.sh <url>}"
HOST=$(echo "$URL" | sed -E 's|https?://([^/:]+).*|\1|')

echo "Diagnosing endpoint: $URL"

# 1. DNS resolution
echo -e "\n--- DNS Resolution ---"
if command -v dig &>/dev/null; then
    dig +short "$HOST" A | head -3
elif command -v nslookup &>/dev/null; then
    nslookup "$HOST" 2>/dev/null | grep -A2 "Name:" | head -5
else
    getent hosts "$HOST" | head -3
fi

# 2. TCP connectivity
echo -e "\n--- TCP Connectivity ---"
PORT=443
if echo "$URL" | grep -q "^http://"; then PORT=80; fi

if command -v nc &>/dev/null; then
    if nc -z -w5 "$HOST" "$PORT" 2>/dev/null; then
        echo "TCP connection to ${HOST}:${PORT} succeeded"
    else
        echo "TCP connection to ${HOST}:${PORT} FAILED" >&2
        exit 1
    fi
elif command -v timeout &>/dev/null; then
    if timeout 5 bash -c "echo >/dev/tcp/$HOST/$PORT" 2>/dev/null; then
        echo "TCP connection to ${HOST}:${PORT} succeeded"
    else
        echo "TCP connection to ${HOST}:${PORT} FAILED" >&2
        exit 1
    fi
fi

# 3. HTTP request with timing
echo -e "\n--- HTTP Request ---"
if command -v curl &>/dev/null; then
    curl -sS -o /dev/null -w "Status: %{http_code}\nLatency: %{time_total}s\nRedirects: %{num_redirects}\nRemote IP: %{remote_ip}\n" \
        --max-time 15 --location "$URL"
elif command -v wget &>/dev/null; then
    wget --spider --timeout=15 -S "$URL" 2>&1 | head -10
fi

echo -e "\n--- Diagnosis Complete ---"
echo "Endpoint $URL is reachable."
exit 0
