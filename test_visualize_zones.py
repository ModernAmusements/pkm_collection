#!/usr/bin/env python3
"""
Visualize zone extraction for test images.
Displays zones in docs folder for verification.
"""

import sys
sys.path.insert(0, '.')

from PIL import Image, ImageDraw, ImageFilter
import pytesseract
from extract_batch import (
    preprocess_image, ZONES_POKEMON, ZONES_TRAINER
)

TEST_IMAGE = "screenshots/test/IMG_1147.PNG"
OUTPUT_DIR = "docs"


def detect_card_type(img):
    """Detect if card is Trainer or Pokemon based on Zone 1 text"""
    w, h = img.size
    
    # Try Pokemon zone 1: y=0 to y=137
    zone1_pkm = img.crop((0, 0, w, 137))
    gray = zone1_pkm.convert('L')
    text_pkm = pytesseract.image_to_string(gray, lang='deu').upper()
    
    print(f"  Pokemon Zone 1 (0-137): {text_pkm[:60]}")
    
    if 'KP' in text_pkm or 'HP' in text_pkm:
        return False
    
    trainer_keywords = ['TRAINER', 'ARTIKEL', 'STADION', 'UNTERSTÜTZUNG', 'SPEZIAL', 'ITEM']
    for keyword in trainer_keywords:
        if keyword in text_pkm:
            return True
    
    # Try Trainer zone 1: y=0 to y=87
    zone1_trn = img.crop((0, 0, w, 87))
    gray = zone1_trn.convert('L')
    text_trn = pytesseract.image_to_string(gray, lang='deu').upper()
    
    print(f"  Trainer Zone 1 (0-87): {text_trn[:60]}")
    
    for keyword in trainer_keywords:
        if keyword in text_trn:
            return True
    
    return False


def visualize_zones(img, zones, is_trainer):
    """Extract and save all zones with labels"""
    
    w, h = img.size
    
    if is_trainer:
        zone_names = {
            1: "Zone 1: Type",
            2: "Zone 2: Name (OCR)",
            3: "Zone 3: Artwork",
            4: "Zone 4: Effect (OCR)",
            5: "Zone 5: Extra (OCR)",
        }
    else:
        zone_names = {
            1: "Zone 1: Name+HP+Energy (OCR)",
            2: "Zone 2: Evolution",
            3: "Zone 3: Artwork",
            4: "Zone 4: Card# (OCR)",
            5: "Zone 5: Attacks",
            6: "Zone 6: Weakness+Retreat",
        }
    
    prefix = "trainer" if is_trainer else "pokemon"
    
    print(f"\nExtracting {len(zones)} zones:\n")
    
    for zone_num, (y1, y2) in zones.items():
        zone = img.crop((0, y1, w, y2))
        
        zone_label = zone_names.get(zone_num, f"Zone {zone_num}")
        print(f"  {zone_label} ({y1}-{y2}px)")
        
        filename = f"{OUTPUT_DIR}/{prefix}_z{zone_num}.png"
        zone.save(filename)


def main():
    print(f"Processing: {TEST_IMAGE}\n")
    
    img = preprocess_image(TEST_IMAGE)
    print(f"Preprocessed image size: {img.size} (should be ~1380px height)")
    
    print("\nDetecting card type:")
    is_trainer = detect_card_type(img)
    card_type = "Trainer" if is_trainer else "Pokemon"
    print(f"\n==> Detected: {card_type}")
    
    zones = ZONES_TRAINER if is_trainer else ZONES_POKEMON
    
    visualize_zones(img, zones, is_trainer)
    
    prefix = "trainer" if is_trainer else "pokemon"
    img.save(f"{OUTPUT_DIR}/{prefix}_preprocessed.png")
    
    print(f"\nAll files saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
