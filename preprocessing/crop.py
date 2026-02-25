#!/usr/bin/env python3
"""
Image preprocessing - Crop and scale card images to standard size.
Matches V1's preprocessing exactly.
"""

from PIL import Image
from dataclasses import dataclass


@dataclass
class CropConfig:
    """Configuration for card cropping - matching V1 exactly."""
    left: float = 0.0855   # 8.55% from left
    right: float = 0.0855  # 8.55% from right  
    top: float = 0.1386    # 13.86% from top
    bottom: float = 0.3164  # 31.64% from bottom


class CardCropper:
    """Standardize card image to consistent size - matching V1."""
    
    def __init__(self, config: CropConfig | None = None):
        self.config = config if config is not None else CropConfig()
    
    def process(self, image_path: str) -> Image.Image:
        """Process single image - matching V1 exactly."""
        img = Image.open(image_path)
        img = self._fix_orientation(img)
        img = self._crop_card(img)
        return img
    
    def process_image(self, img: Image.Image) -> Image.Image:
        """Process already-loaded image."""
        img = self._fix_orientation(img)
        img = self._crop_card(img)
        return img
    
    def _fix_orientation(self, img: Image.Image) -> Image.Image:
        """Detect and fix card orientation (portrait vs landscape)."""
        if img.width > img.height:
            img = img.rotate(-90, expand=True)
        return img
    
    def _crop_card(self, img: Image.Image) -> Image.Image:
        """Crop to card region - exactly matching V1 approach."""
        w, h = img.size
        c = self.config
        
        # Crop all sides using percentages (like V1)
        left = int(w * c.left)
        right = w - int(w * c.right)
        top = int(h * c.top)
        bottom = h - int(h * c.bottom)
        
        return img.crop((left, top, right, bottom))


def preprocess_image(image_path: str) -> Image.Image:
    """Convenience function - process single image."""
    cropper = CardCropper()
    return cropper.process(image_path)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 -m preprocessing.crop <image_path>")
        sys.exit(1)
    
    img = preprocess_image(sys.argv[1])
    print(f"Processed image: {img.size}")
    
    # Save debug output
    img.save("debug_preprocessed.png")
    print("Saved to debug_preprocessed.png")
