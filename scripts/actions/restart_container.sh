#!/bin/bash
# Restart a Docker container. Allowlisted script for aigis.
# Usage: restart_container.sh <container_name>
set -e
if [ -z "$1" ]; then
  echo "Usage: restart_container.sh <container_name>"
  exit 1
fi
docker restart "$1"
