#!/bin/bash

# Configuration
BASE_DIR="/home/horrible/hydropi"
SETUP_DIR="$BASE_DIR/setup"
SERVICES_FILE="$SETUP_DIR/services.txt"
SERVICES_DIR="$SETUP_DIR/services"
VENV_DIR="$BASE_DIR/venv"
REQUIREMENTS_FILE="$SETUP_DIR/requirements.txt"

echo "Starting HydroPi setup..."

# Update and upgrade the system
echo "Updating and upgrading the system..."
sudo apt update && sudo apt upgrade -y

# Install Python, pip, and venv if not already installed
echo "Installing required system packages..."
sudo apt install -y python3 python3-pip python3-venv

# Set up Python virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR" || {
        echo "Failed to create virtual environment. Exiting."
        exit 1
    }
else
    echo "Virtual environment already exists at $VENV_DIR"
fi

echo "Activating the virtual environment..."
source "$VENV_DIR/bin/activate" || {
    echo "Failed to activate the virtual environment. Exiting."
    exit 1
}

# Install Python dependencies
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Installing Python dependencies from $REQUIREMENTS_FILE..."
    pip install -r "$REQUIREMENTS_FILE" || {
        echo "Failed to install Python dependencies. Exiting."
        deactivate
        exit 1
    }
else
    echo "No requirements.txt found in $REQUIREMENTS_FILE. Skipping dependency installation."
fi

# Deactivate virtual environment
deactivate
echo "Python environment setup complete."

# Check for services configuration
if [ ! -f "$SERVICES_FILE" ]; then
    echo "Error: $SERVICES_FILE not found. Please create a services.txt file with service names."
    exit 1
fi

if [ ! -d "$SERVICES_DIR" ]; then
    echo "Error: $SERVICES_DIR directory not found. Please create the directory and add service files."
    exit 1
fi

# Set up services
echo "Setting up services listed in $SERVICES_FILE..."
while IFS= read -r SERVICE_NAME || [[ -n "$SERVICE_NAME" ]]; do
    [[ -z "$SERVICE_NAME" || "$SERVICE_NAME" == \#* ]] && continue

    SERVICE_FILE="$SERVICES_DIR/$SERVICE_NAME"
    SYSTEMD_SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"

    echo "Processing $SERVICE_NAME..."

    if [ ! -f "$SERVICE_FILE" ]; then
        echo "Error: Service file $SERVICE_FILE not found. Skipping..."
        continue
    fi

    if [ ! -f "$SYSTEMD_SERVICE_PATH" ]; then
        echo "$SERVICE_NAME does not exist. Creating it..."
        sudo cp "$SERVICE_FILE" "$SYSTEMD_SERVICE_PATH"
    else
        echo "$SERVICE_NAME already exists. Updating it..."
        sudo cp "$SERVICE_FILE" "$SYSTEMD_SERVICE_PATH"
    fi

    echo "Reloading systemd daemon..."
    sudo systemctl daemon-reload

    if ! systemctl is-enabled --quiet "$SERVICE_NAME"; then
        echo "Enabling $SERVICE_NAME to start on boot..."
        sudo systemctl enable "$SERVICE_NAME"
    fi

    echo "Restarting $SERVICE_NAME..."
    sudo systemctl restart "$SERVICE_NAME"

    sudo systemctl status "$SERVICE_NAME" --no-pager
done < "$SERVICES_FILE"

echo "Service setup complete!"
echo "HydroPi setup finished!"
