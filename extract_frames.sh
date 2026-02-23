#!/bin/bash

cd "$(dirname "$0")"

SCRIPT_DIR="$(pwd)"
CAPTURE_DIR="$SCRIPT_DIR/screenshots"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="$CAPTURE_DIR/$TIMESTAMP"

echo "=== Pokémon TCG Pocket Screen Capture ==="
echo ""

echo "INSTRUCTIONS:"
echo "1. Connect iPhone to Mac via USB"
echo "2. Open QuickTime on Mac"
echo "3. File > New Movie Recording"
echo "4. Click the dropdown arrow and select your iPhone"
echo "5. Click the Record button (or press Cmd+R)"
echo "6. Switch to iPhone and scroll through ALL your cards"
echo "7. When done, stop recording in QuickTime"
echo ""
echo "What is the filename of your recording?"
echo "(It's usually in ~/Movies/ or you can drag it here)"
echo ""
read -p "Recording filename: " VIDEO_PATH

if [ ! -f "$VIDEO_PATH" ]; then
    VIDEO_PATH="$HOME/Movies/$VIDEO_PATH"
fi

if [ ! -f "$VIDEO_PATH" ]; then
    echo "Error: File not found. Try running the script again with the correct path."
    exit 1
fi

echo ""
echo "Extracting frames from: $VIDEO_PATH"
mkdir -p "$OUTPUT_DIR"
echo "Saving to: $OUTPUT_DIR"
echo ""

ffmpeg -i "$VIDEO_PATH" -vf fps=2 "$OUTPUT_DIR/screenshot_%04d.png" -hide_banner

COUNT=$(ls -1 "$OUTPUT_DIR" | wc -l)

echo ""
echo "Done! Extracted $COUNT screenshots"
echo "Location: $OUTPUT_DIR"
