#!/usr/bin/env python3
"""Show OCR output for each zone"""
from PIL import Image
import pytesseract

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

print("=" * 60)
print("POKEMON CARD - Zone Outputs")
print("=" * 60)

img = preprocess_image("screenshots/test/pkm_card.png")

for zone_num in [1, 4, 5, 6]:
    zone = extract_zone(img, zone_num, False)
    text = pytesseract.image_to_string(zone, config='--psm 6')
    print(f"\n--- Zone {zone_num} ---")
    print(text[:200])

print("\n" + "=" * 60)
print("TRAINER CARD - Zone Outputs")
print("=" * 60)

trainer_img = preprocess_image("screenshots/test/trainer_card.png")

for zone_num in [2, 4, 5]:
    zone = extract_zone(trainer_img, zone_num, True)
    text = pytesseract.image_to_string(zone, config='--psm 6')
    print(f"\n--- Zone {zone_num} ---")
    print(text[:200])
