#!/bin/bash

# Home Assistant Development Server Start Script
# For Ökofen Pellematic Compact Integration Testing

cd "$(dirname "$0")/.." || exit 1  # run from the repository root

echo "🏠 Starting Home Assistant Development Server..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 Config Directory: $(pwd)/config"
echo "🔧 Integration: Ökofen Pellematic Compact"
echo "🌐 Web UI: http://localhost:8123"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "ℹ️  First start will take a while (onboarding setup)"
echo "ℹ️  To stop: Press Ctrl+C"
echo ""
echo "📝 Integration Setup:"
echo "   1. Navigate to: http://localhost:8123/config/integrations"
echo "   2. Click '+ Add Integration'"
echo "   3. Search for 'Ökofen Pellematic Compact'"
echo "   4. Enter your Ökofen API URL"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Activate virtual environment
source .venv/bin/activate

# Start Home Assistant
hass -c config --debug
