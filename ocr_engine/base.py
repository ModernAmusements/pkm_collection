#!/usr/bin/env python3
"""
OCR Engine - Multi-pass OCR with result validation.
"""

import re
from dataclasses import dataclass
from typing import Any
from PIL import Image, ImageEnhance
import pytesseract


@dataclass
class OCRResult:
    """Result from OCR processing."""
    text: str
    confidence: float
    lang: str
    method: str


class OCREngine:
    """Multi-pass OCR engine with validation."""
    
    # PSM modes to try
    PSM_MODES = ['6', '4', '3', '11']
    
    # Languages to try
    LANGUAGES = ['deu', 'eng']
    
    def __init__(self):
        self.results: list[OCRResult] = []
    
    def process(self, zone_img: Image.Image, 
                preprocess: bool = True,
                contrast: float = 2.0) -> OCRResult:
        """
        Process a zone with multiple OCR passes.
        
        Args:
            zone_img: Input image
            preprocess: Whether to apply preprocessing
            contrast: Contrast enhancement level
            
        Returns:
            Best OCRResult
        """
        all_results: list[OCRResult] = []
        
        # Pass 1: Standard preprocessing
        if preprocess:
            processed = self._preprocess(zone_img, contrast)
            all_results.extend(self._ocr_pass(processed))
        
        # Pass 2: Higher contrast
        processed = self._preprocess(zone_img, contrast * 1.5)
        all_results.extend(self._ocr_pass(processed))
        
        # Pass 3: Raw image (no preprocessing)
        all_results.extend(self._ocr_pass(zone_img))
        
        # Select best result
        return self._select_best(all_results)
    
    def _preprocess(self, img: Image.Image, contrast: float) -> Image.Image:
        """Apply preprocessing to zone image."""
        gray = img.convert('L')
        enhancer = ImageEnhance.Contrast(gray)
        gray = enhancer.enhance(contrast)
        
        # Sharpen for text
        enhancer = ImageEnhance.Sharpness(gray)
        return enhancer.enhance(1.5)
    
    def _ocr_pass(self, img: Image.Image) -> list[OCRResult]:
        """Single OCR pass with multiple PSM modes and languages."""
        results = []
        
        for psm in self.PSM_MODES:
            config = f'--psm {psm}'
            
            for lang in self.LANGUAGES:
                try:
                    text = pytesseract.image_to_string(img, lang=lang, config=config)
                    text = text.strip()
                    
                    if text and len(text) > 2:
                        # Get confidence
                        data = pytesseract.image_to_data(
                            img, lang=lang, config=config,
                            output_type=pytesseract.Output.DICT
                        )
                        conf = self._calculate_confidence(data)
                        
                        results.append(OCRResult(
                            text=text,
                            confidence=conf,
                            lang=lang,
                            method=f"psm={psm},lang={lang}"
                        ))
                except Exception:
                    continue
        
        return results
    
    def _calculate_confidence(self, data: dict) -> float:
        """Calculate average confidence from OCR data."""
        confidences = [
            int(c) for c in data['conf'] 
            if c != '-1' and int(c) > 0
        ]
        
        if not confidences:
            return 0.0
        
        return sum(confidences) / len(confidences)
    
    def _select_best(self, results: list[OCRResult]) -> OCRResult:
        """Select best result based on confidence and validity."""
        # Filter valid results
        valid = [r for r in results if self._validate_text(r.text)]
        
        if valid:
            return max(valid, key=lambda r: r.confidence)
        
        if results:
            return max(results, key=lambda r: r.confidence)
        
        return OCRResult(text="", confidence=0.0, lang="", method="none")
    
    def _validate_text(self, text: str) -> bool:
        """Validate that OCR result contains reasonable text."""
        if not text:
            return False
        
        # Check for minimum length
        if len(text) < 2:
            return False
        
        # Check for printable characters ratio
        printable = sum(c.isprintable() for c in text)
        ratio = printable / len(text)
        
        return ratio > 0.5


def ocr_zone(zone_img: Image.Image) -> tuple[str, float]:
    """Convenience function to OCR a zone."""
    engine = OCREngine()
    result = engine.process(zone_img)
    return result.text, result.confidence


if __name__ == "__main__":
    from preprocessing import preprocess_image
    from extraction import detect_card_type, ZoneExtractor, CardType
    
    # Test with Pokemon card
    img = preprocess_image("screenshots/test/pkm_card.png")
    
    card_type = detect_card_type(img)
    print(f"Card type: {card_type.value}")
    
    extractor = ZoneExtractor()
    zone = extractor.extract(img, 'name', card_type)
    
    if zone:
        result = OCREngine().process(zone)
        print(f"OCR Result: {result.text[:100]}")
        print(f"Confidence: {result.confidence}")
        print(f"Method: {result.method}")
