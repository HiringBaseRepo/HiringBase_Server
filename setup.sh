#!/bin/bash
# Setup script for Smart Resume Screening System

set -e

echo "🚀 Setting up Smart Resume Screening System..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Please edit .env with your actual credentials"
fi

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your Neon DB URL, R2 keys, and HF token"
echo "2. Run: alembic upgrade head"
echo "3. Run: uvicorn app.main:app --reload"
