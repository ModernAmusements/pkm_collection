#!/usr/bin/env python3
"""Debug energy detection - save Zone 1 for analysis"""
from PIL import Image
import os

# Load test image
img_path = "screenshots/test/pkm_card.png"
img = Image.open(img_path)

# Rotate if needed
w, h = img.size
if w > h:
    img = img.rotate(-90, expand=True)
    w, h = img.size

# Crop percentages
CROP_LEFT_PCT = 0.0855
CROP_RIGHT_PCT = 0.0855
CROP_TOP_PCT = 0.1386
CROP_BOTTOM_PCT = 0.3164

left = int(w * CROP_LEFT_PCT)
right = w - int(w * CROP_RIGHT_PCT)
top = int(h * CROP_TOP_PCT)
bottom = h - int(h * CROP_BOTTOM_PCT)

cropped = img.crop((left, top, right, bottom))

# Zone 1 (Pokemon): 0-10%
w2, h2 = cropped.size
zone1 = cropped.crop((0, 0, w2, int(h2 * 0.10)))

# Save for inspection
zone1.save("debug_zone1.png")

# Sample pixels from different regions
rgb = zone1.convert('RGB')
print(f"Zone1 size: {zone1.size}")

# Check corners and center
test_points = [
    (10, 10),
    (30, 10),
    (10, 30),
    (w2//2, 10),
    (5, 5),
]

for x, y in test_points:
    if x < w2 and y < h2:
        pixel = rgb.getpixel((x, y))
        print(f"Pixel at ({x},{y}): {pixel}")

# Check for orange (Fighting/Ground)
print("\n--- Looking for orange pixels ---")
w1, h1 = zone1.size
total_orange = 0
for x in range(w1):
    for y in range(h1):
        r, g, b = rgb.getpixel((x, y))
        if 180 <= r <= 255 and 80 <= g <= 180 and 0 <= b <= 80:
            total_orange += 1
print(f"Orange pixels found: {total_orange}")
