#!/bin/bash

# ─────────────────────────────────────────────────────────────────────────────
# HydroPi Setup Script
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR="/home/horrible/hydropi"
SETUP_DIR="$BASE_DIR/setup"
SERVICES_FILE="$SETUP_DIR/services.txt"
SERVICES_DIR="$SETUP_DIR/services"
VENV_DIR="$BASE_DIR/venv"
REQUIREMENTS_FILE="$SETUP_DIR/requirements.txt"

# ── Colors & styles ──────────────────────────────────────────────────────────
RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

BLACK='\033[0;30m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[0;37m'

BG_BLUE='\033[44m'

# ── Step tracking ─────────────────────────────────────────────────────────────
TOTAL_STEPS=6
CURRENT_STEP=0
ERRORS=0

# ── Helpers ──────────────────────────────────────────────────────────────────

banner() {
  echo ""
  echo -e "${CYAN}${BOLD}"
  echo "  ██╗  ██╗██╗   ██╗██████╗ ██████╗  ██████╗ ██████╗ ██╗"
  echo "  ██║  ██║╚██╗ ██╔╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗██║"
  echo "  ███████║ ╚████╔╝ ██║  ██║██████╔╝██║   ██║██████╔╝██║"
  echo "  ██╔══██║  ╚██╔╝  ██║  ██║██╔══██╗██║   ██║██╔═══╝ ██║"
  echo "  ██║  ██║   ██║   ██████╔╝██║  ██║╚██████╔╝██║     ██║"
  echo "  ╚═╝  ╚═╝   ╚═╝   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝"
  echo -e "${RESET}"
  echo -e "  ${DIM}Tilt Hydrometer + Raspberry Pi Bridge${RESET}"
  echo ""
}

progress_bar() {
  local step=$1
  local total=$2
  local width=40
  local filled=$(( width * step / total ))
  local empty=$(( width - filled ))
  local bar=""

  for (( i=0; i<filled; i++ )); do bar+="█"; done
  for (( i=0; i<empty; i++ )); do bar+="░"; done

  echo -ne "\r  ${DIM}[${RESET}${GREEN}${bar}${RESET}${DIM}]${RESET} ${BOLD}${step}/${total}${RESET}"
}

step_header() {
  CURRENT_STEP=$(( CURRENT_STEP + 1 ))
  echo ""
  echo ""
  progress_bar "$CURRENT_STEP" "$TOTAL_STEPS"
  echo ""
  echo -e "  ${BLUE}${BOLD}▶ Step ${CURRENT_STEP}/${TOTAL_STEPS}${RESET}  ${BOLD}$1${RESET}"
  echo -e "  ${DIM}$(printf '─%.0s' {1..55})${RESET}"
}

ok() {
  echo -e "  ${GREEN}✓${RESET}  $1"
}

info() {
  echo -e "  ${CYAN}·${RESET}  $1"
}

warn() {
  echo -e "  ${YELLOW}⚠${RESET}  $1"
}

fail() {
  echo -e "  ${RED}✗${RESET}  $1"
  ERRORS=$(( ERRORS + 1 ))
}

die() {
  echo ""
  echo -e "  ${RED}${BOLD}✗ Fatal: $1${RESET}"
  echo ""
  exit 1
}

run_quiet() {
  local label="$1"; shift
  local logfile
  logfile=$(mktemp)
  local spinner=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
  local i=0

  echo -ne "  ${CYAN}${spinner[$i]}${RESET}  ${label}…"

  "$@" >"$logfile" 2>&1 &
  local pid=$!

  while kill -0 "$pid" 2>/dev/null; do
    i=$(( (i + 1) % ${#spinner[@]} ))
    echo -ne "\r  ${CYAN}${spinner[$i]}${RESET}  ${label}…"
    sleep 0.1
  done

  wait "$pid"
  local exit_code=$?
  rm -f "$logfile"

  if [ $exit_code -eq 0 ]; then
    echo -e "\r  ${GREEN}✓${RESET}  ${label}"
  else
    echo -e "\r  ${RED}✗${RESET}  ${label} ${DIM}(exit ${exit_code})${RESET}"
    ERRORS=$(( ERRORS + 1 ))
  fi

  return $exit_code
}

# ── Main ──────────────────────────────────────────────────────────────────────

clear
banner

echo -e "  ${DIM}Host:$(hostname)   $(date '+%Y-%m-%d %H:%M')${RESET}"
echo ""

# ── Step 1: System update ─────────────────────────────────────────────────────
step_header "System update & upgrade"
run_quiet "Updating package lists" sudo apt update
run_quiet "Upgrading installed packages" sudo apt upgrade -y

# ── Step 2: System packages ───────────────────────────────────────────────────
step_header "Installing system packages"
run_quiet "Installing python3, pip, venv, bluetooth tools" \
  sudo apt install -y python3 python3-pip python3-venv bluetooth bluez rfkill

# ── Step 3: Python virtual environment ────────────────────────────────────────
step_header "Python virtual environment"
if [ ! -d "$VENV_DIR" ]; then
  run_quiet "Creating virtual environment at $VENV_DIR" python3 -m venv "$VENV_DIR" \
    || die "Failed to create virtual environment"
else
  ok "Virtual environment already exists — skipping creation"
fi

info "Activating virtual environment"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate" || die "Failed to activate virtual environment"

# ── Step 4: Python dependencies ───────────────────────────────────────────────
step_header "Python dependencies"
if [ -f "$REQUIREMENTS_FILE" ]; then
  run_quiet "Installing packages from requirements.txt" pip install -r "$REQUIREMENTS_FILE" \
    || { deactivate; die "Failed to install Python dependencies"; }
else
  warn "No requirements.txt found at $REQUIREMENTS_FILE — skipping"
fi
deactivate
ok "Virtual environment deactivated"

# ── Step 5: Service files ─────────────────────────────────────────────────────
step_header "Registering systemd services"

[ -f "$SERVICES_FILE" ] || die "$SERVICES_FILE not found"
[ -d "$SERVICES_DIR" ]  || die "$SERVICES_DIR directory not found"

while IFS= read -r SERVICE_NAME || [[ -n "$SERVICE_NAME" ]]; do
  [[ -z "$SERVICE_NAME" || "$SERVICE_NAME" == \#* ]] && continue

  SERVICE_FILE="$SERVICES_DIR/$SERVICE_NAME"
  SYSTEMD_PATH="/etc/systemd/system/$SERVICE_NAME"

  if [ ! -f "$SERVICE_FILE" ]; then
    fail "Service file not found: $SERVICE_FILE — skipping"
    continue
  fi

  sudo cp "$SERVICE_FILE" "$SYSTEMD_PATH"
  ok "Copied $SERVICE_NAME → $SYSTEMD_PATH"
done < "$SERVICES_FILE"

run_quiet "Reloading systemd daemon" sudo systemctl daemon-reload

# ── Step 6: Enable & start services ──────────────────────────────────────────
step_header "Enabling & starting services"

while IFS= read -r SERVICE_NAME || [[ -n "$SERVICE_NAME" ]]; do
  [[ -z "$SERVICE_NAME" || "$SERVICE_NAME" == \#* ]] && continue
  [ -f "$SERVICES_DIR/$SERVICE_NAME" ] || continue

  if ! systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    run_quiet "Enabling $SERVICE_NAME" sudo systemctl enable "$SERVICE_NAME"
  else
    ok "$SERVICE_NAME already enabled"
  fi

  run_quiet "Restarting $SERVICE_NAME" sudo systemctl restart "$SERVICE_NAME"

  if systemctl is-active --quiet "$SERVICE_NAME"; then
    ok "$SERVICE_NAME is ${GREEN}active${RESET}"
  else
    fail "$SERVICE_NAME failed to start"
    sudo systemctl status "$SERVICE_NAME" --no-pager -l 2>&1 | sed 's/^/     /'
  fi
done < "$SERVICES_FILE"

# ── Summary ───────────────────────────────────────────────────────────────────

progress_bar "$TOTAL_STEPS" "$TOTAL_STEPS"
echo ""
echo ""

if [ $ERRORS -eq 0 ]; then
  echo -e "  ${GREEN}${BOLD}✓ Setup complete!${RESET}  All steps finished without errors."
else
  echo -e "  ${YELLOW}${BOLD}⚠ Setup finished with ${ERRORS} error(s).${RESET}  Review the output above."
fi

echo ""
echo -e "  ${DIM}Run ${RESET}${BOLD}journalctl -u tilt-scanner -f${RESET}${DIM} to watch live logs.${RESET}"
echo ""
