#!/bin/bash

# Configuration
BASE_DIR="/home/horrible/hydropi"
SETUP_DIR="$BASE_DIR/setup"
SERVICES_FILE="$SETUP_DIR/services.txt"
SERVICES_DIR="$SETUP_DIR/services"
VENV_DIR="$BASE_DIR/venv"
REQUIREMENTS_FILE="$SETUP_DIR/requirements.txt"
NEXTJS_DIR="$BASE_DIR/hydropi-next"

echo "Starting HydroPi setup..."

echo "Configuring sudo to allow 'who' command without a password..."

# Define the sudoers rule
SUDO_RULE="horrible ALL=(ALL) NOPASSWD: /usr/bin/who"

# Check if the rule already exists in the sudoers file
if ! sudo grep -q "^$SUDO_RULE" /etc/sudoers; then
    echo "$SUDO_RULE" | sudo tee -a /etc/sudoers > /dev/null
    echo "Sudo rule added: $SUDO_RULE"
else
    echo "Sudo rule already exists: $SUDO_RULE"
fi

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

# Install Node.js and npm
echo "Installing Node.js and npm..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install -y nodejs
else
    echo "Node.js is already installed."
fi

echo "Node.js version: $(node -v)"
echo "npm version: $(npm -v)"

# Install and build the Next.js site
if [ -d "$NEXTJS_DIR" ]; then
    echo "Installing npm dependencies for Next.js site..."
    cd "$NEXTJS_DIR"
    npm install || {
        echo "Failed to install npm dependencies. Exiting."
        exit 1
    }

    echo "Building the Next.js site..."
    npm run build || {
        echo "Failed to build the Next.js site. Exiting."
        exit 1
    }
    cd "$BASE_DIR"
else
    echo "Next.js directory not found at $NEXTJS_DIR. Skipping Next.js setup."
fi

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
    # Skip empty lines and comments
    [[ -z "$SERVICE_NAME" || "$SERVICE_NAME" == \#* ]] && continue

    SERVICE_FILE="$SERVICES_DIR/$SERVICE_NAME"
    SYSTEMD_SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"

    echo "Processing $SERVICE_NAME..."

    if [ ! -f "$SERVICE_FILE" ]; then
        echo "Error: Service file $SERVICE_FILE not found. Skipping..."
        continue
    fi

    # Check if the service file already exists in systemd
    if [ ! -f "$SYSTEMD_SERVICE_PATH" ]; then
        echo "$SERVICE_NAME does not exist. Creating it..."
        sudo cp "$SERVICE_FILE" "$SYSTEMD_SERVICE_PATH"
    else
        echo "$SERVICE_NAME already exists. Updating it..."
        sudo cp "$SERVICE_FILE" "$SYSTEMD_SERVICE_PATH"
    fi

    # Reload systemd to apply changes
    echo "Reloading systemd daemon..."
    sudo systemctl daemon-reload

    # Enable the service to start at boot
    if ! systemctl is-enabled --quiet "$SERVICE_NAME"; then
        echo "Enabling $SERVICE_NAME to start on boot..."
        sudo systemctl enable "$SERVICE_NAME"
    fi

    # Restart the service
    echo "Restarting $SERVICE_NAME..."
    sudo systemctl restart "$SERVICE_NAME"

    # Check the service status
    sudo systemctl status "$SERVICE_NAME" --no-pager
done < "$SERVICES_FILE"

echo "Verifying services..."
while IFS= read -r SERVICE_NAME || [[ -n "$SERVICE_NAME" ]]; do
    [[ -z "$SERVICE_NAME" || "$SERVICE_NAME" == \#* ]] && continue
    echo "Checking status of $SERVICE_NAME..."
    sudo systemctl status "$SERVICE_NAME" --no-pager
done < "$SERVICES_FILE"

echo "Service setup complete!"

echo "HydroPi setup finished!"
