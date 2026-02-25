#!/usr/bin/env python3
"""Test preprocessing and zone extraction for trainer cards"""

from PIL import Image
import os

CROP_SIDES = 0.085
CROP_HEIGHT = 555
SCALE = 3

ZONES_TRAINER = {
    1: (0, 41),
    2: (41, 81),
    3: (81, 289),
    4: (289, 480),
    5: (480, 554),
}

TEST_DIR = "test_output"

def preprocess_image(image_path):
    img = Image.open(image_path)
    w, h = img.size
    
    left = int(w * CROP_SIDES)
    right = w - left
    img = img.crop((left, 0, right, h))
    
    top = int(h * 0.14)
    img = img.crop((0, top, img.width, top + CROP_HEIGHT))
    
    return img

def extract_zones(img, is_trainer=False):
    zones = ZONES_TRAINER if is_trainer else None
    results = {}
    
    for z_num, (y1, y2) in zones.items():
        zone = img.crop((0, y1, img.width, y2))
        zone_scaled = zone.resize((zone.width * SCALE, zone.height * SCALE))
        results[z_num] = zone_scaled
        print(f"Zone {z_num}: {y1}-{y2}px -> {zone_scaled.size}")
    
    return results

def main():
    import sys
    
    # Use stadium card as trainer example
    image_path = "screenshots/all/card_001.png"
    
    print(f"Processing: {image_path}\n")
    
    # Preprocess
    img = preprocess_image(image_path)
    print(f"Preprocessed: {img.size}\n")
    
    # Extract zones
    print("Extracting zones:")
    zones = extract_zones(img, is_trainer=True)
    
    # Save zones
    os.makedirs(TEST_DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(image_path))[0]
    for z_num, zone_img in zones.items():
        zone_img.save(f"{TEST_DIR}/{base}_z{z_num}.png")
    
    print(f"\nSaved to {TEST_DIR}/")

if __name__ == "__main__":
    main()
