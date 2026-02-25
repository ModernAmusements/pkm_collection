#!/usr/bin/env python3
"""Test detect_card_type and zone extraction"""

import sys
sys.path.insert(0, '.')

from PIL import Image
import pytesseract
from extract_batch import (
    preprocess_image, extract_zone, ZONES_POKEMON, ZONES_TRAINER
)

CROP_LEFT = 100
CROP_RIGHT = 100
CROP_TOP = 351
CROP_BOTTOM = 801
CARD_HEIGHT = 1380

def detect_card_type(img):
    """Detect if card is Trainer or Pokemon based on Zone 1 text"""
    # Use extract_zone which does: crop → greyscale → sharpen → scale
    zone1 = extract_zone(img, 1, is_trainer=False)
    if zone1 is None:
        return False
    
    text = pytesseract.image_to_string(zone1, lang='deu').upper()
    
    print(f"  Pokemon Zone 1 OCR: {text[:60]}")
    
    # Check for Pokemon indicators
    if 'KP' in text or 'HP' in text:
        return False
    
    # Check for Trainer keywords
    trainer_keywords = ['TRAINER', 'ARTIKEL', 'STADION', 'UNTERSTÜTZUNG', 'SPEZIAL', 'ITEM']
    for keyword in trainer_keywords:
        if keyword in text:
            return True
    
    # Try Trainer zone 1
    zone1_trainer = extract_zone(img, 1, is_trainer=True)
    if zone1_trainer:
        text_trn = pytesseract.image_to_string(zone1_trainer, lang='deu').upper()
        print(f"  Trainer Zone 1 OCR: {text_trn[:60]}")
        for keyword in trainer_keywords:
            if keyword in text_trn:
                return True
    
    return False

def main():
    import sys
    # Use test image or command line argument
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = "screenshots/test/IMG_1147.PNG"
    
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
        
        # OCR the zone (high res, no scaling)
        gray = zone.convert('L')
        text = pytesseract.image_to_string(gray, lang='deu')
        
        print(f"Zone {z_num} ({y1}-{y2}): {text[:80]}")
        
        zone.save(f"test_output/card_001_{'trn' if is_trainer else 'pkm'}_z{z_num}.png")
    
    print(f"\nSaved to test_output/")

if __name__ == "__main__":
    main()
