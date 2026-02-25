#!/usr/bin/env python3
"""Debug energy detection - check pixel distribution"""
from PIL import Image

img_path = "screenshots/test/pkm_card.png"
img = Image.open(img_path)
w, h = img.size
if w > h:
    img = img.rotate(-90, expand=True)
    w, h = img.size

CROP_LEFT_PCT = 0.0855
CROP_RIGHT_PCT = 0.0855
CROP_TOP_PCT = 0.1386
CROP_BOTTOM_PCT = 0.3164

left = int(w * CROP_LEFT_PCT)
right = w - int(w * CROP_RIGHT_PCT)
top = int(h * CROP_TOP_PCT)
bottom = h - int(h * CROP_BOTTOM_PCT)
cropped = img.crop((left, top, right, bottom))

w2, h2 = cropped.size
zone1 = cropped.crop((0, 0, w2, int(h2 * 0.10)))

rgb = zone1.convert('RGB')
pixels = list(rgb.getdata())

# Count by color category
counts = {
    'white/gray': 0,
    'red': 0,
    'blue': 0,
    'yellow': 0,
    'green': 0,
    'orange': 0,
    'purple': 0,
    'pink': 0,
    'brown': 0,
}

for r, g, b in pixels:
    # Skip white/gray (background)
    if r > 200 and g > 200 and b > 200:
        counts['white/gray'] += 1
        continue
    
    # Orange/Brown (Ground/Fighting)
    if r >= 150 and g <= 180 and b <= 100:
        counts['orange'] += 1
    # Red
    elif r >= 200 and g <= 100 and b <= 100:
        counts['red'] += 1
    # Blue
    elif b >= 150 and r <= 100 and g <= 150:
        counts['blue'] += 1
    # Yellow
    elif r >= 200 and g >= 200 and b <= 100:
        counts['yellow'] += 1
    # Green
    elif g >= 150 and r <= 100 and b <= 100:
        counts['green'] += 1
    # Purple
    elif r >= 150 and b >= 150 and g <= 100:
        counts['purple'] += 1
    # Pink
    elif r >= 200 and b >= 150 and g <= 150:
        counts['pink'] += 1

print(f"Zone1 pixel counts: {counts}")
print(f"Total pixels: {len(pixels)}")
