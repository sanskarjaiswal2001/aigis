#!/bin/bash
# Register AIgis health check cron job in OpenClaw.
# Run every 5 minutes (isolated session). Adjust schedule/delivery as needed.
# Use --announce --channel X --to Y for delivery; omit for internal-only.

openclaw cron add \
  --name "AIgis health check" \
  --every 300000 \
  --session isolated \
  --message "Run the infrastructure health check. Use the aigis tool to collect and evaluate. If severity is WARN or CRITICAL, explain the anomalies and deliver a concise summary."
