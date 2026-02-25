#!/usr/bin/env python3
"""Visualize extracted zones for debugging"""
from PIL import Image
import os

def preprocess_image(image_path):
    img = Image.open(image_path)
    w, h = img.size
    
    if w > h:
        img = img.rotate(-90, expand=True)
        w, h = h, w
    
    CROP_LEFT_PCT = 0.0855
    CROP_RIGHT_PCT = 0.0855
    CROP_TOP_PCT = 0.1386
    CROP_BOTTOM_PCT = 0.3164
    
    left = int(w * CROP_LEFT_PCT)
    right = w - int(w * CROP_RIGHT_PCT)
    top = int(h * CROP_TOP_PCT)
    bottom = h - int(h * CROP_BOTTOM_PCT)
    
    return img.crop((left, top, right, bottom))

ZONES_POKEMON = {
    1: (0.00, 0.10),
    2: (0.10, 0.12),
    3: (0.12, 0.47),
    4: (0.47, 0.51),
    5: (0.51, 0.84),
    6: (0.84, 1.00),
}

ZONES_TRAINER = {
    1: (0.00, 0.06),
    2: (0.06, 0.15),
    3: (0.15, 0.43),
    4: (0.43, 0.87),
    5: (0.87, 1.00),
}

def extract_zone(img, zone_num, is_trainer=False):
    zones = ZONES_TRAINER if is_trainer else ZONES_POKEMON
    if zone_num not in zones:
        return None
    
    w, h = img.size
    y1_pct, y2_pct = zones[zone_num]
    y1 = int(y1_pct * h)
    y2 = int(y2_pct * h)
    
    return img.crop((0, y1, w, y2))

# Test with Pass card
img_path = "screenshots/test/pkm_card.png"
img = preprocess_image(img_path)

print("=== Pokemon Card Zones ===\n")

for zone_num in [1, 4, 5, 6]:
    zone = extract_zone(img, zone_num, False)
    zone.save(f"debug_zone_{zone_num}.png")
    print(f"Zone {zone_num}: {ZONES_POKEMON[zone_num]} - saved to debug_zone_{zone_num}.png")

print("\n=== Trainer Card Zones ===\n")

# Also test trainer
trainer_path = "screenshots/test/trainer_card.png"
trainer_img = preprocess_image(trainer_path)

for zone_num in [2, 4, 5]:
    zone = extract_zone(trainer_img, zone_num, True)
    zone.save(f"debug_trainer_zone_{zone_num}.png")
    print(f"Zone {zone_num}: {ZONES_TRAINER[zone_num]} - saved to debug_trainer_zone_{zone_num}.png")
