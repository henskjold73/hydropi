#!/bin/bash

echo "Starting HydroPi setup..."

# Update and upgrade the system
sudo apt update && sudo apt upgrade -y

# Install Python, pip, and venv
sudo apt install -y python3 python3-pip python3-venv

# Create a virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate the virtual environment
echo "Activating the virtual environment..."
. venv/bin/activate

# Install required Python packages using the virtual environment's pip
echo "Installing Python dependencies..."
./venv/bin/pip install -r setup/requirements.txt

echo "HydroPi setup complete! To activate the virtual environment, use: . venv/bin/activate"
