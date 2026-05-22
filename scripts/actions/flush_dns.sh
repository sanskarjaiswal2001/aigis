#!/bin/bash
# Flush DNS resolver cache.
set -euo pipefail

echo "Flushing DNS resolver cache..."

if command -v systemd-resolve &>/dev/null; then
    sudo systemd-resolve --flush-caches
    echo "systemd-resolved cache flushed"
    systemd-resolve --statistics 2>/dev/null | head -5 || true
elif command -v resolvectl &>/dev/null; then
    sudo resolvectl flush-caches
    echo "resolvectl cache flushed"
    resolvectl statistics 2>/dev/null | head -5 || true
elif [ -f /etc/init.d/nscd ]; then
    sudo /etc/init.d/nscd restart
    echo "nscd restarted"
elif command -v dscacheutil &>/dev/null; then
    sudo dscacheutil -flushcache
    sudo killall -HUP mDNSResponder 2>/dev/null || true
    echo "macOS DNS cache flushed"
else
    echo "No known DNS cache service found — cache may clear on its own" >&2
    exit 1
fi

echo "DNS cache flush complete."
exit 0
