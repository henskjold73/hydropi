#!/bin/bash
# Installs and starts the HydroPi dashboard on tty1.
# Run from the repo root: bash setup/install_dashboard.sh

set -e

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_SRC="$BASE_DIR/setup/services/hydropi-dashboard.service"
SERVICE_DST="/etc/systemd/system/hydropi-dashboard.service"

echo "→ Masking getty@tty1 so the dashboard can own the console..."
sudo systemctl mask getty@tty1.service

echo "→ Installing service file..."
sudo cp "$SERVICE_SRC" "$SERVICE_DST"

echo "→ Reloading systemd..."
sudo systemctl daemon-reload

echo "→ Enabling hydropi-dashboard..."
sudo systemctl enable hydropi-dashboard

echo "→ Starting hydropi-dashboard..."
sudo systemctl restart hydropi-dashboard

echo ""
echo "✓ Done. Dashboard is running on tty1."
echo "  To watch logs: journalctl -u hydropi-dashboard -f"
echo "  To uninstall:  sudo systemctl disable hydropi-dashboard && sudo systemctl unmask getty@tty1.service"
