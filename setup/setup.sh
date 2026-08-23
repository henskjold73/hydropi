#!/bin/bash

# ─────────────────────────────────────────────────────────────────────────────
# HydroPi Setup Script
# Usage: ./setup.sh [--demo]
#   --demo  Show the full visual flow with fake progress (no real changes made)
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SETUP_DIR="$BASE_DIR/setup"
SERVICES_FILE="$SETUP_DIR/services.txt"
SERVICES_DIR="$SETUP_DIR/services"
VENV_DIR="$BASE_DIR/venv"
REQUIREMENTS_FILE="$SETUP_DIR/requirements.txt"
LOGS_DIR="$BASE_DIR/logs"
ENV_FILE="$BASE_DIR/.env"
ENV_EXAMPLE="$BASE_DIR/.env.example"
LOGROTATE_SRC="$SETUP_DIR/logrotate-hydropi"
LOGROTATE_DST="/etc/logrotate.d/hydropi"
CURRENT_USER="$(whoami)"

DEMO=false
for arg in "$@"; do
  [[ "$arg" == "--demo" ]] && DEMO=true
done

# ── Colors & styles ──────────────────────────────────────────────────────────
RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'

# ── Step tracking ─────────────────────────────────────────────────────────────
TOTAL_STEPS=8
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
  if $DEMO; then
    echo -e "  ${YELLOW}${BOLD}  ── DEMO MODE ──  no changes will be made${RESET}"
  fi
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

ok()   { echo -e "  ${GREEN}✓${RESET}  $1"; }
info() { echo -e "  ${CYAN}·${RESET}  $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}  $1"; }

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
  local spinner=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
  local i=0

  echo -ne "  ${CYAN}${spinner[$i]}${RESET}  ${label}…"

  if $DEMO; then
    local end=$(( $(date +%s) + 3 ))
    while (( $(date +%s) < end )); do
      i=$(( (i + 1) % ${#spinner[@]} ))
      echo -ne "\r  ${CYAN}${spinner[$i]}${RESET}  ${label}…"
      sleep 0.1
    done
    echo -e "\r  ${GREEN}✓${RESET}  ${label} ${DIM}[demo]${RESET}"
    return 0
  fi

  local logfile
  logfile=$(mktemp)

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

# Substitute __BASEDIR__ and __USER__ in a template file and write to dest.
install_template() {
  local src="$1"
  local dst="$2"
  sed -e "s|__BASEDIR__|$BASE_DIR|g" \
      -e "s|__USER__|$CURRENT_USER|g" \
      "$src" | sudo tee "$dst" > /dev/null
}

# ── Main ──────────────────────────────────────────────────────────────────────

clear
banner

echo -e "  ${DIM}Host: $(hostname)   User: $CURRENT_USER   $(date '+%Y-%m-%d %H:%M')${RESET}"
echo -e "  ${DIM}Base: $BASE_DIR${RESET}"
echo ""

# ── Step 1: System update ─────────────────────────────────────────────────────
step_header "System update & upgrade"
run_quiet "Updating package lists"        sudo apt update
run_quiet "Upgrading installed packages"  sudo apt upgrade -y

# ── Step 2: System packages ───────────────────────────────────────────────────
step_header "Installing system packages"
run_quiet "Installing python3, pip, venv, bluetooth tools" \
  sudo apt install -y python3 python3-pip python3-venv bluetooth bluez rfkill

# ── Step 3: Python virtual environment ────────────────────────────────────────
step_header "Python virtual environment"
if $DEMO; then
  run_quiet "Creating virtual environment at $VENV_DIR" true
else
  if [ ! -d "$VENV_DIR" ]; then
    run_quiet "Creating virtual environment at $VENV_DIR" python3 -m venv "$VENV_DIR" \
      || die "Failed to create virtual environment"
  else
    ok "Virtual environment already exists — skipping creation"
  fi
  info "Activating virtual environment"
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate" || die "Failed to activate virtual environment"
fi

# ── Step 4: Python dependencies ───────────────────────────────────────────────
step_header "Python dependencies"
if $DEMO; then
  run_quiet "Installing packages from requirements.txt" true
else
  if [ -f "$REQUIREMENTS_FILE" ]; then
    run_quiet "Installing packages from requirements.txt" pip install -r "$REQUIREMENTS_FILE" \
      || { deactivate; die "Failed to install Python dependencies"; }
  else
    warn "No requirements.txt found at $REQUIREMENTS_FILE — skipping"
  fi
  deactivate
  ok "Virtual environment deactivated"
fi

# ── Step 5: Directories & environment file ────────────────────────────────────
step_header "Directories & environment file"
if $DEMO; then
  run_quiet "Creating logs directory" true
  run_quiet "Checking .env file" true
else
  if [ ! -d "$LOGS_DIR" ]; then
    mkdir -p "$LOGS_DIR"
    ok "Created $LOGS_DIR"
  else
    ok "Logs directory already exists"
  fi

  if [ -f "$ENV_FILE" ]; then
    ok ".env already exists — skipping"
  elif [ -f "$ENV_EXAMPLE" ]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    warn ".env created from .env.example — edit it before starting the service"
  else
    warn "No .env or .env.example found — create $ENV_FILE manually"
  fi
fi

# ── Step 6: Log rotation ──────────────────────────────────────────────────────
step_header "Log rotation"
if $DEMO; then
  run_quiet "Installing logrotate config" true
else
  if [ -f "$LOGROTATE_SRC" ]; then
    info "Substituting paths for user '$CURRENT_USER' in logrotate config..."
    install_template "$LOGROTATE_SRC" "$LOGROTATE_DST"
    ok "Logrotate config installed at $LOGROTATE_DST"
  else
    warn "Logrotate config not found at $LOGROTATE_SRC — skipping"
  fi
fi

# ── Step 7: Service files ─────────────────────────────────────────────────────
step_header "Registering systemd services"
if $DEMO; then
  run_quiet "Copying service files to /etc/systemd/system" true
  run_quiet "Reloading systemd daemon" true
else
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

    info "Substituting paths for user '$CURRENT_USER' in $SERVICE_NAME..."
    install_template "$SERVICE_FILE" "$SYSTEMD_PATH"
    ok "Installed $SERVICE_NAME → $SYSTEMD_PATH"
  done < "$SERVICES_FILE"

  run_quiet "Reloading systemd daemon" sudo systemctl daemon-reload
fi

# ── Step 8: Enable & start services ──────────────────────────────────────────
step_header "Enabling & starting services"
if $DEMO; then
  run_quiet "Enabling tilt-scanner.service" true
  run_quiet "Restarting tilt-scanner.service" true
  ok "tilt-scanner.service is ${GREEN}active${RESET} ${DIM}[demo]${RESET}"
else
  [ -f "$SERVICES_FILE" ] || die "$SERVICES_FILE not found"

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
fi

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
if [ ! -f "$ENV_FILE" ] || grep -q '<your-' "$ENV_FILE" 2>/dev/null; then
  echo -e "  ${YELLOW}⚠${RESET}  Edit ${BOLD}.env${RESET} with your brewery ID and API key before starting the service."
fi
echo -e "  ${DIM}Run ${RESET}${BOLD}journalctl -u tilt-scanner -f${RESET}${DIM} to watch live logs.${RESET}"
echo ""
