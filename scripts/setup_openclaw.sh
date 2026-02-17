#!/bin/bash
# Setup OpenClaw one folder above Aigis.
# Creates ../openclaw, installs OpenClaw, links Aigis skill, and prepares config.
# Run from Aigis repo root: ./scripts/setup_openclaw.sh

set -e

AIGIS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PARENT="$(dirname "$AIGIS_ROOT")"
OPENCLAW_ROOT="${PARENT}/openclaw"

echo "Aigis:  $AIGIS_ROOT"
echo "OpenClaw: $OPENCLAW_ROOT"

mkdir -p "$OPENCLAW_ROOT"
cd "$OPENCLAW_ROOT"

# Install OpenClaw via npm if not present
if ! command -v openclaw &>/dev/null; then
  echo "Installing OpenClaw globally..."
  npm install -g openclaw@latest
fi

# Create .openclaw structure under ../openclaw (OPENCLAW_HOME)
mkdir -p "${OPENCLAW_ROOT}/.openclaw/workspace/skills"
SKILL_LINK="${OPENCLAW_ROOT}/.openclaw/workspace/skills/aigis"
rm -f "$SKILL_LINK"
ln -s "$AIGIS_ROOT/openclaw/skills/aigis" "$SKILL_LINK"
echo "Linked Aigis skill."

# Config so OpenClaw loads Aigis skill from workspace
CONFIG="${OPENCLAW_ROOT}/.openclaw/openclaw.json"
mkdir -p "$(dirname "$CONFIG")"
if [ ! -f "$CONFIG" ]; then
  cat > "$CONFIG" << EOF
{
  "gateway": { "mode": "local" },
  "skills": {
    "load": {
      "extraDirs": ["$AIGIS_ROOT/openclaw/skills"]
    }
  }
}
EOF
  echo "Created config at $CONFIG"
else
  echo "Config exists. Add to skills.load.extraDirs if needed: $AIGIS_ROOT/openclaw/skills"
fi

# Remind about onboarding
echo "If first-time: export OPENCLAW_HOME=$OPENCLAW_ROOT && openclaw onboard --install-daemon"

echo ""
echo "Setup complete. To run OpenClaw from ../openclaw:"
echo "  export OPENCLAW_HOME=$OPENCLAW_ROOT"
echo "  openclaw gateway"
echo ""
echo "Register cron:"
echo "  export OPENCLAW_HOME=$OPENCLAW_ROOT"
echo "  $AIGIS_ROOT/scripts/setup_openclaw_cron.sh"
