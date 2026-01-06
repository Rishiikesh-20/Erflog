#!/bin/bash
# Auto-Apply Setup Script
# Run this to install all necessary dependencies for auto-apply functionality

echo "🚀 Installing Auto-Apply Dependencies..."
echo ""

# Navigate to backend directory
cd backend

# Install Python dependencies
echo "📦 Installing Python packages..."
pip install "browser-use>=0.11.0" "playwright>=1.40.0"

# Install Playwright browsers
echo "🌐 Installing Chromium browser..."
playwright install chromium

# Verify installation
echo ""
echo "✅ Checking installations..."
python -c "import browser_use; print(f'✓ browser-use {browser_use.__version__}')"
python -c "import playwright; print('✓ playwright installed')"

echo ""
echo "🎉 Auto-Apply setup complete!"
echo ""
echo "Next steps:"
echo "1. Ensure GEMINI_API_KEY is set in your .env file"
echo "2. Start backend: uvicorn main:app --reload --port 8000"
echo "3. Try auto-apply from the frontend /jobs/[id]/apply page"
echo ""
echo "See AUTO_APPLY_SETUP.md for full documentation."
