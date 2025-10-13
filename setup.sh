#!/bin/bash

# Setup script for Scrum Master Agent

echo "🤖 Setting up Scrum Master Agent..."
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Create credentials file if it doesn't exist
echo ""
if [ ! -f config/credentials.properties ]; then
    echo "Creating credentials.properties from template..."
    cp config/credentials.properties.example config/credentials.properties
    echo "⚠️  Please edit config/credentials.properties with your actual credentials"
else
    echo "credentials.properties already exists"
fi

# Create necessary directories
echo ""
echo "Creating necessary directories..."
mkdir -p reports

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit config/credentials.properties with your Jira, Azure OpenAI, and Email credentials"
echo "2. (Optional) Edit config/config.yaml to customize settings"
echo "3. Test your connection: python -m src.main test"
echo "4. Start the application: python -m src.main web"
echo ""
echo "For more information, see README.md"


