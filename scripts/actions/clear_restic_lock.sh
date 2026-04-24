#!/usr/bin/env bash
set -euo pipefail
restic unlock
echo "Stale lock cleared. You can now run restic backup."
