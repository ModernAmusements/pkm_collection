#!/usr/bin/env python3
"""Test detect_card_type and zone extraction"""

import sys
sys.path.insert(0, '.')

from PIL import Image
import pytesseract
from extract_batch import (
    preprocess_image, extract_zone, ZONES_POKEMON, ZONES_TRAINER
)

CROP_SIDES = 0.085
CROP_HEIGHT = 555
SCALE = 3

def detect_card_type(img):
    """Detect if card is Trainer or Pokemon based on Zone 1 text"""
    zone1 = extract_zone(img, 1)
    gray = zone1.convert('L')
    text = pytesseract.image_to_string(gray, lang='deu').upper()
    
    print(f"Zone 1 OCR text: {text[:100]}")
    
    trainer_keywords = ['TRAINER', 'ARTIKEL', 'STADION', 'UNTERSTÜTZUNG', 'SPEZIAL']
    for keyword in trainer_keywords:
        if keyword in text:
            return True
    
    return False

def main():
    image_path = "screenshots/to_process/card_001.png"
    print(f"Testing: {image_path}\n")
    
    # Preprocess
    img = preprocess_image(image_path)
    print(f"Preprocessed: {img.size}\n")
    
    # Detect card type
    is_trainer = detect_card_type(img)
    card_type = "TRAINER" if is_trainer else "POKEMON"
    print(f"\nDetected: {card_type}\n")
    
    # Use zones based on detection
    zones = ZONES_TRAINER if is_trainer else ZONES_POKEMON
    print(f"Using zones: {'TRAINER' if is_trainer else 'POKEMON'}\n")
    
    # Extract and save all zones
    for z_num, (y1, y2) in zones.items():
        zone = img.crop((0, y1, img.width, y2))
        zone_scaled = zone.resize((zone.width * SCALE, zone.height * SCALE))
        
        # OCR the zone
        gray = zone_scaled.convert('L')
        text = pytesseract.image_to_string(gray, lang='deu')
        
        print(f"Zone {z_num} ({y1}-{y2}): {text[:80]}")
        
        zone_scaled.save(f"test_output/card_001_{'trn' if is_trainer else 'pkm'}_z{z_num}.png")
    
    print(f"\nSaved to test_output/")

if __name__ == "__main__":
    main()
