#!/bin/bash
# Run restic backup. Allowlisted script for aigis.
# Uses RESTIC_REPOSITORY and RESTIC_PASSWORD env. No params required.
set -e
if ! command -v restic &>/dev/null; then
  echo "restic not found"
  exit 1
fi
restic backup / 2>/dev/null || true
