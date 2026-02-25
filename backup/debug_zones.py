#!/usr/bin/env python3
"""Debug script to visualize all zones for images in to_process"""

from PIL import Image
import pytesseract
import os

# Process all images in to_process
to_process_dir = "screenshots/to_process"
output_dir = "screenshots/debug_zones"
os.makedirs(output_dir, exist_ok=True)

# Zone definitions
ZONES_POKEMON = {
    1: (0.00, 0.10, "Zone1_TopBar"),
    2: (0.10, 0.12, "Zone2_Evolution"),
    3: (0.12, 0.47, "Zone3_Artwork"),
    4: (0.47, 0.51, "Zone4_CardNum"),
    5: (0.51, 0.84, "Zone5_Attacks"),
    6: (0.84, 1.00, "Zone6_BottomInfo"),
}

ZONES_TRAINER = {
    1: (0.00, 0.06, "Zone1_TopLabel"),
    2: (0.06, 0.15, "Zone2_Name"),
    3: (0.15, 0.43, "Zone3_Artwork"),
    4: (0.43, 0.87, "Zone4_Effect"),
    5: (0.87, 1.00, "Zone5_SetInfo"),
}

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

def detect_card_type(img):
    w, h = img.size
    zone1 = img.crop((0, 0, w, int(h * 0.06)))
    text = pytesseract.image_to_string(zone1, config='--psm 6')
    text = text.upper()
    
    if any(x in text for x in ['HP', 'KP', 'POKEMON']):
        return False
    if any(x in text for x in ['TRAINER', 'ITEM', 'STADION']):
        return True
    return False

def extract_zone(img, zone_num, is_trainer=False):
    zones = ZONES_TRAINER if is_trainer else ZONES_POKEMON
    if zone_num not in zones:
        return None
    
    w, h = img.size
    zone_def = zones[zone_num]
    if len(zone_def) >= 2:
        y1_pct, y2_pct = zone_def[0], zone_def[1]
    else:
        y1_pct, y2_pct = zone_def
    y1 = int(y1_pct * h)
    y2 = int(y2_pct * h)
    
    return img.crop((0, y1, w, y2))

# Process each image
for filename in os.listdir(to_process_dir):
    if not filename.endswith('.png'):
        continue
    
    filepath = os.path.join(to_process_dir, filename)
    print(f"\n{'='*60}")
    print(f"Image: {filename}")
    print('='*60)
    
    # Preprocess
    img = preprocess_image(filepath)
    print(f"Preprocessed size: {img.size}")
    
    # Detect card type
    is_trainer = detect_card_type(img)
    zones = ZONES_TRAINER if is_trainer else ZONES_POKEMON
    card_type = "TRAINER" if is_trainer else "POKEMON"
    print(f"Detected: {card_type}")
    
    # Extract each zone
    for zone_num in zones:
        zone = extract_zone(img, zone_num, is_trainer)
        name = zones[zone_num][2] if len(zones[zone_num]) > 2 else f"Zone{zone_num}"
        
        if zone:
            # Save zone image
            out_path = os.path.join(output_dir, f"{filename.replace('.png','')}_{name}.png")
            zone.save(out_path)
            
            # OCR
            text = pytesseract.image_to_string(zone, config='--psm 6')
            print(f"\n{name} (Zone {zone_num}):")
            print(f"  OCR: {text.strip()[:100] if text.strip() else '(empty)'}")

print(f"\n\nSaved zones to: {output_dir}/")
