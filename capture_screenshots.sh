#!/bin/bash

cd "$(dirname "$0")"

SCRIPT_DIR="$(pwd)"
CAPTURE_DIR="$SCRIPT_DIR/screenshots"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="$CAPTURE_DIR/$TIMESTAMP"

echo "=== Pokémon TCG Pocket Screenshot Capture ==="
echo ""

if ! command -v idevicescreenshot &> /dev/null; then
    echo "Error: idevicescreenshot not found"
    echo "Run: brew install libimobiledevice"
    exit 1
fi

DEVICE=$(idevice_id -l | head -1)
if [ -z "$DEVICE" ]; then
    echo "Error: No iPhone connected"
    echo "Connect your iPhone via USB and unlock it"
    exit 1
fi

echo "iPhone connected: $DEVICE"
echo ""

mkdir -p "$OUTPUT_DIR"
echo "Screenshots will be saved to: $OUTPUT_DIR"
echo ""

echo "INSTRUCTIONS:"
echo "1. Open Pokémon TCG Pocket on your iPhone"
echo "2. Go to your card collection"
echo "3. Press ENTER to start capturing..."
read -r

echo "Capturing screenshots... (Press Ctrl+C to stop)"
echo ""

COUNT=0
while true; do
    FILENAME="$OUTPUT_DIR/screenshot_$(printf '%04d' $COUNT).png"
    idevicescreenshot -u "$DEVICE" "$FILENAME" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        COUNT=$((COUNT + 1))
        echo "Captured: $FILENAME"
    else
        echo "Error capturing - check iPhone connection"
        break
    fi
    
    sleep 0.5
done

echo ""
echo "Done! Captured $COUNT screenshots"
echo "Location: $OUTPUT_DIR"
