#!/usr/bin/env python3
"""Extract and save all zones for images in to_process"""
from PIL import Image
import os
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
    
    return img.crop((left, top, right, bottom)), (left, top, right, bottom)

ZONES_POKEMON = {
    1: (0.00, 0.10, "Zone1_TopBar_Name_HP"),
    2: (0.10, 0.12, "Zone2_Evolution"),
    3: (0.12, 0.47, "Zone3_Artwork"),
    4: (0.47, 0.51, "Zone4_CardNumber"),
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

def extract_zone(img, zone_num, is_trainer=False):
    zones = ZONES_TRAINER if is_trainer else ZONES_POKEMON
    if zone_num not in zones:
        return None
    
    w, h = img.size
    y1_pct, y2_pct, _ = zones[zone_num]
    y1 = int(y1_pct * h)
    y2 = int(y2_pct * h)
    
    return img.crop((0, y1, w, y2))

def detect_card_type(img):
    # Check Zone 1 for card type indicators
    w, h = img.size
    zone1 = img.crop((0, 0, w, int(h * 0.06)))
    
    text = pytesseract.image_to_string(zone1, config='--psm 6')
    text = text.upper()
    
    # Pokemon indicators
    if any(x in text for x in ['HP', 'KP', 'POKEMON']):
        return False  # Pokemon
    
    # Trainer indicators  
    if any(x in text for x in ['TRAINER', 'ITEM', 'STADION', 'UNTERSTÜTZUNG']):
        return True   # Trainer
    
    return False  # Default to Pokemon

# Process all images in to_process
to_process_dir = "screenshots/to_process"
output_dir = "screenshots/debug_zones"
os.makedirs(output_dir, exist_ok=True)

for filename in os.listdir(to_process_dir):
    if filename.endswith('.png') or filename.endswith('.jpg'):
        filepath = os.path.join(to_process_dir, filename)
        print(f"\n{'='*60}")
        print(f"Processing: {filename}")
        print('='*60)
        
        img, crop_coords = preprocess_image(filepath)
        
        # Detect card type
        is_trainer = detect_card_type(img)
        zones = ZONES_TRAINER if is_trainer else ZONES_POKEMON
        card_type = "TRAINER" if is_trainer else "POKEMON"
        print(f"Detected: {card_type}")
        
        # Extract and save each zone
        for zone_num in zones:
            y1_pct, y2_pct, name = zones[zone_num]
            zone = extract_zone(img, zone_num, is_trainer)
            
            if zone:
                output_path = os.path.join(output_dir, f"{filename.replace('.png','')}_{name}.png")
                zone.save(output_path)
                print(f"  Saved: {name}")
                
                # Also show OCR for each zone
                text = pytesseract.image_to_string(zone, config='--psm 6')
                if text.strip():
                    print(f"    OCR: {text.strip()[:80]}...")
