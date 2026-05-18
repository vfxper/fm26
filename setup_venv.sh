#!/bin/bash
# Telegram Football Manager - Virtual Environment Setup Script for Linux/macOS

echo "========================================"
echo "Telegram Football Manager Setup"
echo "========================================"
echo ""

# Check if Python 3.11 is installed
echo "Checking Python version..."
if ! command -v python3.11 &> /dev/null; then
    echo "ERROR: Python 3.11 is not installed!"
    echo "Please install Python 3.11 from your package manager or https://www.python.org/downloads/"
    exit 1
fi

echo "Python 3.11 found!"
python3.11 --version
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3.11 -m venv venv
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create virtual environment!"
    exit 1
fi

echo "Virtual environment created successfully!"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "To activate the virtual environment in the future, run:"
echo "  source venv/bin/activate"
echo ""
echo "To deactivate, run:"
echo "  deactivate"
echo ""
