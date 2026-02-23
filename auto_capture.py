#!/usr/bin/env python3
import os
import time
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

os.environ['PYAUTOGUI_PAUSE'] = '0.1'
os.environ['PYAUTOGUI_FAILSAFE'] = 'true'

import pyautogui
import pygetwindow

CAPTURE_DIR = os.path.join(SCRIPT_DIR, "screenshots")
TIMESTAMP = time.strftime("%Y%m%d_%H%M%S")
OUTPUT_DIR = os.path.join(CAPTURE_DIR, TIMESTAMP)

INTERVAL = 1.0

def get_quicktime_window():
    titles = pygetwindow.getAllTitles()
    for title in titles:
        if "QuickTime" in title:
            return pygetwindow.getWindowGeometry(title)
    return None

def main():
    print("=== Pokemon TCG Pocket Screenshot Capture ===")
    print()
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Output: {OUTPUT_DIR}")
    print()
    
    geo = get_quicktime_window()
    if not geo:
        print("Error: QuickTime window not found!")
        print("Open QuickTime Player with iPhone streaming first")
        sys.exit(1)
    
    left, top, width, height = geo
    print(f"QuickTime window: ({left}, {top}) {width}x{height}")
    print()
    print("INSTRUCTIONS:")
    print("1. Open QuickTime Player > New Movie Recording > select iPhone")
    print("2. On iPhone, open Pokemon TCG Pocket to card collection")
    print("3. Press ENTER to start...")
    print()
    input()
    
    print("Capturing... (Press Ctrl+C to stop)")
    print()
    
    count = 0
    try:
        while True:
            region = (int(left), int(top), int(width), int(height))
            img = pyautogui.screenshot(region=region)
            
            filename = f"screenshot_{count:04d}.png"
            filepath = os.path.join(OUTPUT_DIR, filename)
            img.save(filepath)
            
            count += 1
            print(f"{count}: {filename}")
            
            time.sleep(INTERVAL)
            
    except KeyboardInterrupt:
        pass
    
    print()
    print(f"Done! Captured {count} screenshots")
    print(f"Location: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
