#!/bin/bash

cd "$(dirname "$0")"

SCRIPT_DIR="$(pwd)"
SCREENSHOTS_DIR="$SCRIPT_DIR/screenshots"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="$SCREENSHOTS_DIR/$TIMESTAMP"

echo "=== Syncing Photos from iPhone ==="
echo ""

mkdir -p "$OUTPUT_DIR"

echo "INSTRUCTIONS:"
echo "1. Connect iPhone to Mac via USB"
echo "2. Open Photos app on Mac"
echo "3. Select your iPhone in the sidebar"
echo "4. Select all new screenshots (Cmd+A)"
echo "5. Click Import Selected (or Cmd+I)"
echo "6. After import, find imported photos in 'Recently Imported'"
echo "7. Select all and drag to: $OUTPUT_DIR"
echo ""
echo "Or use AirDrop to send photos to Mac."
echo ""
echo "Output directory: $OUTPUT_DIR"
echo ""
echo "Press Enter when done..."
read -r

COUNT=$(ls -1 "$OUTPUT_DIR" 2>/dev/null | wc -l)
echo "Total photos: $COUNT"
