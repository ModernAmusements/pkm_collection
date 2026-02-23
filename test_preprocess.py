#!/usr/bin/env python3
"""Test preprocessing function - visualize each step"""

from PIL import Image
import os

CROP_SIDES = 0.085
CROP_HEIGHT = 555

def preprocess_image(image_path):
    """Crop sides, crop to 555px height, return image ready for zone extraction"""
    img = Image.open(image_path)
    w, h = img.size
    
    # Step 1: Crop sides (8.5% from each side)
    left = int(w * CROP_SIDES)
    right = w - left
    img = img.crop((left, 0, right, h))
    
    # Step 2: Crop to 555px height from top (14% from top)
    top = int(h * 0.14)
    img = img.crop((0, top, img.width, top + CROP_HEIGHT))
    
    return img

def test_preprocess(image_path, output_prefix="test"):
    """Test preprocessing and save intermediate steps"""
    os.makedirs(TEST_DIR, exist_ok=True)
    
    original = Image.open(image_path)
    print(f"Original: {original.size}")
    
    # Step 1: Crop sides
    w, h = original.size
    left = int(w * CROP_SIDES)
    right = w - left
    cropped_sides = original.crop((left, 0, right, h))
    cropped_sides.save(f"{output_prefix}_step1_sides.png")
    print(f"After sides crop: {cropped_sides.size}")
    
    # Step 2: Crop height
    top = int(h * 0.14)
    final = original.crop((left, top, right, top + CROP_HEIGHT))
    final.save(f"{output_prefix}_step2_final.png")
    print(f"After height crop: {final.size}")
    
    return final

TEST_DIR = "test_output"

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 test_preprocess.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    prefix = os.path.join(TEST_DIR, os.path.splitext(os.path.basename(image_path))[0])
    
    result = test_preprocess(image_path, prefix)
    print(f"\nFinal: {prefix}_step2_final.png ({result.size})")

if __name__ == "__main__":
    main()
