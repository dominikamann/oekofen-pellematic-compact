#!/bin/bash
# Monitor Home Assistant logs for Ökofen integration activity

echo "=== Monitoring Ökofen Integration Logs ==="
echo "Try to change a value in Home Assistant UI now..."
echo ""

tail -f homeassistant.log | grep --line-buffered -i "oekofen\|send_pellematic_data\|set.*temperature\|set.*mode\|HTTP Error"
