#!/usr/bin/env python3
"""
Image denoising for holographic card processing.
Removes sparkle patterns that confuse OCR.
"""

from PIL import Image, ImageEnhance, ImageFilter
import numpy as np


class HoloDenoiser:
    """Remove holographic sparkle patterns from card images."""
    
    def process(self, img: Image.Image) -> Image.Image:
        """Apply denoising to an image."""
        # Convert to numpy for processing
        arr = np.array(img)
        
        # Apply median filter to remove salt-pepper noise
        # This helps with holo sparkle patterns
        from scipy import ndimage
        
        # Median filter with size 3
        filtered = ndimage.median_filter(arr, size=3)
        
        result = Image.fromarray(filtered)
        
        # Slight smoothing to reduce high-frequency noise
        result = result.filter(ImageFilter.SMOOTH)
        
        return result
    
    def process_zone(self, zone_img: Image.Image) -> Image.Image:
        """Process a specific zone image."""
        # For zones, we want lighter denoising to preserve text
        arr = np.array(zone_img)
        from scipy import ndimage
        
        # Smaller median filter for text zones
        filtered = ndimage.median_filter(arr, size=2)
        
        return Image.fromarray(filtered)


class AdaptiveThreshold:
    """Apply adaptive thresholding for better OCR on text zones."""
    
    def apply(self, img: Image.Image) -> Image.Image:
        """Apply Otsu's thresholding."""
        import cv2
        
        gray = img.convert('L')
        arr = np.array(gray)
        
        # Otsu's thresholding
        _, thresh = cv2.threshold(arr, 0, 255, 
            cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return Image.fromarray(thresh)
    
    def apply_local(self, img: Image.Image, block_size: int = 11) -> Image.Image:
        """Apply local adaptive thresholding."""
        import cv2
        
        gray = img.convert('L')
        arr = np.array(gray)
        
        # Gaussian weighted sum of neighborhood
        thresh = cv2.adaptiveThreshold(
            arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, block_size, 2
        )
        
        return Image.fromarray(thresh)


class ZonePreprocessor:
    """Preprocessing optimized for different zone types."""
    
    def __init__(self):
        self.denoiser = HoloDenoiser()
        self.threshold = AdaptiveThreshold()
    
    def preprocess_for_ocr(self, zone_img: Image.Image, 
                          zone_type: str = "text") -> Image.Image:
        """
        Preprocess zone image for OCR.
        
        Args:
            zone_img: Input image
            zone_type: "text" (name, attacks) or "number" (HP, card number)
        """
        # Convert to grayscale
        gray = zone_img.convert('L')
        
        if zone_type == "text":
            # For text zones: increase contrast more
            enhancer = ImageEnhance.Contrast(gray)
            gray = enhancer.enhance(2.0)
            
            # Sharpen to help with text edges
            enhancer = ImageEnhance.Sharpness(gray)
            gray = enhancer.enhance(1.5)
        
        elif zone_type == "number":
            # For numbers (HP, card#): lighter processing
            enhancer = ImageEnhance.Contrast(gray)
            gray = enhancer.enhance(1.8)
        
        return gray
    
    def preprocess_for_color(self, zone_img: Image.Image) -> Image.Image:
        """Preprocess for color analysis (energy detection)."""
        # Keep original colors, just reduce noise
        return self.denoiser.process_zone(zone_img)


def denoise_image(image_path: str, output_path: str = None) -> Image.Image:
    """Convenience function to denoise an image."""
    denoiser = HoloDenoiser()
    img = Image.open(image_path)
    result = denoiser.process(img)
    
    if output_path:
        result.save(output_path)
    
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 -m preprocessing.denoise <image_path>")
        sys.exit(1)
    
    # Test denoising
    denoiser = HoloDenoiser()
    img = Image.open(sys.argv[1])
    
    print(f"Original: {img.size}")
    
    result = denoiser.process(img)
    print(f"Denoised: {result.size}")
    
    result.save("debug_denoised.png")
    print("Saved to debug_denoised.png")
