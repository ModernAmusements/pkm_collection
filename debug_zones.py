#!/usr/bin/env python3
"""Debug script to find correct zone boundaries"""

from PIL import Image
import pytesseract

# Load image
img = Image.open('screenshots/to_process/card_009.png')
w, h = img.size

# Crop settings
CROP_SIDES = 0.085
CROP_HEIGHT = 555

left = int(w * CROP_SIDES)
right = w - left
img = img.crop((left, 0, right, h))
top = int(h * 0.14)
img = img.crop((0, top, img.width, top + CROP_HEIGHT))

print(f"Preprocessed: {img.size}\n")

# Test different zone boundaries to find name
test_zones = [
    (0, 30),
    (0, 40),
    (0, 50),
    (0, 60),
    (0, 70),
    (10, 50),
    (20, 60),
]

for y1, y2 in test_zones:
    zone = img.crop((0, y1, img.width, y2))
    gray = zone.convert('L')
    text = pytesseract.image_to_string(gray, lang='deu')
    print(f"Zone ({y1:2d}-{y2:2d}): {text[:60]}")
