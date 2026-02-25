#!/usr/bin/env python3
"""
Card type detection - Pokemon vs Trainer classification.
"""

import pytesseract
from PIL import Image
from dataclasses import dataclass

from .zones import CardType, ZoneExtractor


TRAINER_KEYWORDS = [
    'TRAINER', 'ARTIKEL', 'STADION', 'UNTERSTÜTZUNG', 
    'SUPPORTER', 'ITEM', 'STADIUM', 'SPECIAL'
]

POKEMON_INDICATORS = ['KP', 'HP']


@dataclass
class DetectionResult:
    """Result of card type detection."""
    card_type: CardType
    confidence: float
    evidence: list[str]


class CardTypeDetector:
    """Detect whether a card is Pokemon or Trainer."""
    
    def __init__(self):
        self.zone_extractor = ZoneExtractor()
    
    def detect(self, img: Image.Image) -> DetectionResult:
        """Detect card type from preprocessed image."""
        
        # Strategy 1: Check Pokemon zone 1 (name + HP area)
        pokemon_result = self._check_pokemon_indicators(img)
        if pokemon_result:
            return pokemon_result
        
        # Strategy 2: Check Trainer zone 1 (type label)
        trainer_result = self._check_trainer_indicators(img)
        if trainer_result:
            return trainer_result
        
        # Default to Pokemon (more common)
        return DetectionResult(
            card_type=CardType.POKEMON,
            confidence=0.5,
            evidence=["No clear indicators, defaulting to Pokemon"]
        )
    
    def _check_pokemon_indicators(self, img: Image.Image) -> DetectionResult | None:
        """Check for Pokemon-specific indicators."""
        zone = self.zone_extractor.extract(img, 'name', CardType.POKEMON)
        if zone is None:
            # Try hp_bar as fallback
            zone = self.zone_extractor.extract(img, 'hp_bar', CardType.POKEMON)
        
        if zone is None:
            return None
        
        # OCR the zone
        gray = zone.convert('L')
        text = pytesseract.image_to_string(gray, config='--psm 6').upper()
        
        evidence = []
        
        # Check for HP/KP
        for indicator in POKEMON_INDICATORS:
            if indicator in text:
                evidence.append(f"Found '{indicator}'")
                return DetectionResult(
                    card_type=CardType.POKEMON,
                    confidence=0.9,
                    evidence=evidence
                )
        
        return None
    
    def _check_trainer_indicators(self, img: Image.Image) -> DetectionResult | None:
        """Check for Trainer-specific indicators."""
        zone = self.zone_extractor.extract(img, 'type', CardType.TRAINER)
        
        if zone is None:
            return None
        
        # OCR the zone
        gray = zone.convert('L')
        text = pytesseract.image_to_string(gray, config='--psm 6').upper()
        
        evidence = []
        
        for keyword in TRAINER_KEYWORDS:
            if keyword in text:
                evidence.append(f"Found '{keyword}'")
                return DetectionResult(
                    card_type=CardType.TRAINER,
                    confidence=0.9,
                    evidence=evidence
                )
        
        return None


def detect_card_type(img: Image.Image) -> CardType:
    """Convenience function to detect card type."""
    detector = CardTypeDetector()
    result = detector.detect(img)
    return result.card_type


if __name__ == "__main__":
    from preprocessing import preprocess_image
    
    # Test with Pokemon card
    img = preprocess_image("screenshots/test/pkm_card.png")
    detector = CardTypeDetector()
    result = detector.detect(img)
    print(f"Pokemon test card: {result.card_type.value} (confidence: {result.confidence})")
    print(f"  Evidence: {result.evidence}")
    
    # Test with Trainer card
    img = preprocess_image("screenshots/test/trainer_card.png")
    result = detector.detect(img)
    print(f"\nTrainer test card: {result.card_type.value} (confidence: {result.confidence})")
    print(f"  Evidence: {result.evidence}")
