#!/bin/bash
cd "$(dirname "$0")"

echo "=== Pokémon TCG Pocket Capture Script ==="
echo ""
echo "Step 1: Finding your Mac's IP address..."
IP=$(ipconfig getifaddr en0)
echo "Your Mac's IP: $IP"
echo ""
echo "Step 2: Starting mitmproxy..."
echo "Configure your iPhone proxy to: $IP:8080"
echo "Then scroll through your collection in the app."
echo "Press Ctrl+C when done to extract cards."
echo ""

mitmproxy --listen-port 8080 --save-stream mitm_capture

echo ""
echo "Extracting cards..."
python3 extract_full_collection.py

echo ""
echo "Done! Check cards_full.json and my_cards_full.csv"
