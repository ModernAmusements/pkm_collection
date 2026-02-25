#!/usr/bin/env python3
"""
Energy Type Extraction - Text + Color detection.
"""

import re
from dataclasses import dataclass
from PIL import Image
import numpy as np


# German to English energy mapping
GERMAN_TO_ENERGY = {
    'Feuer': 'Fire',
    'Wasser': 'Water', 
    'Elektro': 'Lightning',
    'Pflanze': 'Grass',
    'Kampf': 'Fighting',
    'Psycho': 'Psychic',
    'Unlicht': 'Darkness',
    'Metall': 'Metal',
    'Fee': 'Fairy',
    'Drache': 'Dragon',
    'Farblos': 'Colorless',
}


# Energy color RGB ranges (min, max)
ENERGY_COLORS = {
    'Feuer': ((180, 30, 30), (255, 100, 100)),       # Red
    'Wasser': ((30, 80, 180), (100, 160, 255)),     # Blue
    'Elektro': ((200, 200, 30), (255, 255, 100)),   # Yellow
    'Pflanze': ((30, 130, 30), (100, 220, 100)),    # Green
    'Kampf': ((180, 100, 30), (240, 180, 100)),     # Orange
    'Psycho': ((140, 30, 160), (210, 90, 240)),     # Purple
    'Unlicht': ((30, 30, 80), (90, 90, 140)),       # Dark blue
    'Metall': ((110, 110, 130), (170, 170, 200)),   # Gray
    'Fee': ((200, 120, 180), (255, 180, 220)),      # Pink
    'Drache': ((140, 70, 40), (210, 130, 100)),     # Brown
    'Farblos': ((200, 200, 200), (255, 255, 255)), # White/Light gray
}


@dataclass
class EnergyExtraction:
    """Result of energy type extraction."""
    energy: str | None
    confidence: float
    source: str  # "text" or "color"


class EnergyExtractor:
    """Extract energy type combining text and color detection."""
    
    def __init__(self):
        self.text_extractor = _TextEnergyExtractor()
        self.color_extractor = _ColorEnergyExtractor()
    
    def extract(self, zone_img: Image.Image, ocr_text: str = "") -> EnergyExtraction:
        """
        Extract energy type using both text and color.
        
        Args:
            zone_img: Image of zone containing energy info
            ocr_text: OCR text from the same zone
            
        Returns:
            EnergyExtraction with value and confidence
        """
        # First: try text extraction (higher confidence)
        text_result = self.text_extractor.extract(ocr_text)
        if text_result.energy:
            return text_result
        
        # Fallback: try color detection
        color_result = self.color_extractor.extract(zone_img)
        if color_result.energy:
            return color_result
        
        # No result
        return EnergyExtraction(None, 0.0, "none")
    
    def extract_from_zones(self, name_zone: Image.Image, 
                         attacks_zone: Image.Image = None) -> EnergyExtraction:
        """Extract energy from multiple zones."""
        # Try name zone first
        result = self.color_extractor.extract(name_zone)
        if result.energy:
            return result
        
        # Try attacks zone
        if attacks_zone:
            result = self.color_extractor.extract(attacks_zone)
            if result.energy:
                return result
        
        return EnergyExtraction(None, 0.0, "none")


class _TextEnergyExtractor:
    """Extract energy from OCR text."""
    
    def extract(self, text: str) -> EnergyExtraction:
        if not text:
            return EnergyExtraction(None, 0.0, "text")
        
        text_upper = text.upper()
        
        # Check German keywords
        for ger, eng in GERMAN_TO_ENERGY.items():
            if ger.upper() in text_upper or eng.upper() in text_upper:
                return EnergyExtraction(eng, 0.95, "text")
        
        return EnergyExtraction(None, 0.0, "text")


class _ColorEnergyExtractor:
    """Extract energy from image colors."""
    
    # Focus regions (percentages) to scan for energy colors
    FOCUS_REGIONS = [
        (0.0, 0.0, 1.0, 0.3),    # Top 30%
        (0.7, 0.0, 1.0, 0.5),    # Top-right corner
    ]
    
    def extract(self, zone_img: Image.Image) -> EnergyExtraction:
        """Detect energy type from dominant color in focus regions."""
        if zone_img is None:
            return EnergyExtraction(None, 0.0, "color")
        
        rgb = zone_img.convert('RGB')
        w, h = rgb.size
        pixels = list(rgb.getdata())
        
        # Count pixels matching each energy color
        energy_votes: dict[str, int] = {}
        
        for energy, ((r1, g1, b1), (r2, g2, b2)) in ENERGY_COLORS.items():
            count = 0
            for pr, pg, pb in pixels:
                # Check if pixel is in color range
                if (min(r1, r2) <= pr <= max(r1, r2) and
                    min(g1, g2) <= pg <= max(g1, g2) and
                    min(b1, b2) <= pb <= max(b1, b2)):
                    count += 1
            energy_votes[energy] = count
        
        # Get max votes
        max_votes = max(energy_votes.values())
        
        # Need minimum threshold
        if max_votes < 50:
            return EnergyExtraction(None, 0.0, "color")
        
        detected = max(energy_votes, key=energy_votes.get)
        
        # Special handling for Farblos (Colorless)
        # If Farblos wins but other energies have significant votes, use that
        if detected == 'Farblos':
            for energy, votes in energy_votes.items():
                if energy != 'Farblos' and votes > max_votes * 0.3:
                    detected = energy
                    break
        
        # Convert to English
        english = GERMAN_TO_ENERGY.get(detected, detected)
        
        # Confidence based on vote margin
        confidence = min(0.8, max_votes / 5000)
        
        return EnergyExtraction(english, confidence, "color")


def extract_energy(zone_img: Image.Image, ocr_text: str = "") -> str | None:
    """Convenience function to extract energy."""
    result = EnergyExtractor().extract(zone_img, ocr_text)
    return result.energy


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
        energy = EnergyExtractor()
        result = energy.extract(zone)
        print(f"Energy: {result.energy}, confidence: {result.confidence}, source: {result.source}")
