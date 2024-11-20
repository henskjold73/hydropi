#!/bin/bash

echo "Starting HydroPi setup..."

# Update and upgrade the system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install -y python3 python3-pip

# Install required Python packages
pip3 install -r setup/requirements.txt

echo "HydroPi setup complete!"