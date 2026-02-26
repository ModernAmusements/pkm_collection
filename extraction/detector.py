#!/usr/bin/env python3
"""
Card type detection - Pokemon vs Trainer classification.
Also detects:
- Pokemon variants: Regular, ex, Tera, Full Art, Illustration Rare, Gold
- Trainer subtypes: Item, Supporter, Stadium
"""

import pytesseract
from PIL import Image
from dataclasses import dataclass
from enum import Enum

from .zones import CardType, ZoneExtractor


class TrainerSubtype(Enum):
    """Trainer card subtypes."""
    ITEM = "item"
    SUPPORTER = "supporter"
    STADIUM = "stadium"
    UNKNOWN = "unknown"


class PokemonVariant(Enum):
    """Pokemon card variants."""
    REGULAR = "regular"
    EX = "ex"           # Pokemon ex
    TERA = "tera"       # Tera Pokemon ex
    FULL_ART = "full_art"
    ILLUSTRATION_RARE = "illustration_rare"
    GOLD = "gold"
    UNKNOWN = "unknown"


# German translations
TRAINER_KEYWORDS = {
    'ITEM': TrainerSubtype.ITEM,
    'ARTIKEL': TrainerSubtype.ITEM,
    'SUPORTER': TrainerSubtype.SUPPORTER,
    'SUPPORTER': TrainerSubtype.SUPPORTER,
    'UNTERSTÜTZUNG': TrainerSubtype.SUPPORTER,
    'UNTERSTUTZER': TrainerSubtype.SUPPORTER,
    'UNTERSTITZER': TrainerSubtype.SUPPORTER,  # OCR error
    'STADIUM': TrainerSubtype.STADIUM,
    'STADION': TrainerSubtype.STADIUM,
    'TRAINER': TrainerSubtype.UNKNOWN,
    'TRAINING': TrainerSubtype.STADIUM,
    'KAMPFPLATZ': TrainerSubtype.STADIUM,
    'AUSRISTUNG': TrainerSubtype.ITEM,  # Pokemon Tool in German
}

POKEMON_INDICATORS = ['KP', 'HP']

# Pokemon ex indicator (lowercase ex)
EX_INDICATORS = ['ex', 'EX']
TERA_INDICATORS = ['TERA', 'Tera', 'tera']
FULL_ART_INDICATORS = ['FULL', 'ART']
ILLUSTRATION_INDICATORS = ['ILLUSTRATION', 'IR', 'SIR']
GOLD_INDICATORS = ['GOLD', '◊◊', '☆☆☆☆']


@dataclass
class DetectionResult:
    """Result of card type detection."""
    card_type: CardType
    confidence: float
    evidence: list[str]
    trainer_subtype: TrainerSubtype = TrainerSubtype.UNKNOWN
    pokemon_variant: PokemonVariant = PokemonVariant.UNKNOWN


class CardTypeDetector:
    """Detect whether a card is Pokemon or Trainer."""
    
    def __init__(self):
        self.zone_extractor = ZoneExtractor()
    
    def detect(self, img: Image.Image) -> DetectionResult:
        """Detect card type from preprocessed image."""
        
        # Strategy 1: Check Trainer FIRST (more common issue with misdetection)
        trainer_result = self._check_trainer_indicators(img)
        if trainer_result:
            return trainer_result
        
        # Strategy 2: Check Pokemon zone 1 (name + HP area)
        pokemon_result = self._check_pokemon_indicators(img)
        if pokemon_result:
            return pokemon_result
        
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
            return None
        
        # OCR the zone
        text = pytesseract.image_to_string(zone, config='--psm 6').upper()
        
        # Handle common OCR errors
        text = text.replace('ES=', 'PHASE')  # PHASE 1 -> ES=1
        text = text.replace('EAS=', 'PHASE')  # PHASE -> EAS=
        text = text.replace('XE', 'HP')       # HP -> XE
        
        evidence = []
        variant = PokemonVariant.REGULAR
        
        # Check for HP/KP first
        hp_found = False
        for indicator in POKEMON_INDICATORS:
            if indicator in text:
                evidence.append(f"Found '{indicator}'")
                hp_found = True
                break
        
        if not hp_found:
            return None
        
        # Check for Pokemon variants
        # ex (lowercase)
        for indicator in EX_INDICATORS:
            if indicator in text:
                # Check if it's Tera
                if any(t in text for t in TERA_INDICATORS):
                    variant = PokemonVariant.TERA
                    evidence.append("Found Tera")
                else:
                    variant = PokemonVariant.EX
                    evidence.append("Found ex")
                break
        
        # Full Art
        if any(t in text for t in FULL_ART_INDICATORS):
            variant = PokemonVariant.FULL_ART
            evidence.append("Found Full Art")
        
        # Illustration Rare
        if any(t in text for t in ILLUSTRATION_INDICATORS):
            variant = PokemonVariant.ILLUSTRATION_RARE
            evidence.append("Found Illustration Rare")
        
        # Gold
        if any(t in text for t in GOLD_INDICATORS):
            variant = PokemonVariant.GOLD
            evidence.append("Found Gold")
        
        return DetectionResult(
            card_type=CardType.POKEMON,
            confidence=0.9,
            evidence=evidence,
            pokemon_variant=variant
        )
    
    def _check_trainer_indicators(self, img: Image.Image) -> DetectionResult | None:
        """Check for Trainer-specific indicators."""
        zone = self.zone_extractor.extract(img, 'type', CardType.TRAINER)
        
        if zone is None:
            return None
        
        # OCR the zone
        text = pytesseract.image_to_string(zone, config='--psm 6').upper()
        
        evidence = []
        subtype = TrainerSubtype.UNKNOWN
        
        for keyword, subtype_enum in TRAINER_KEYWORDS.items():
            if keyword in text:
                evidence.append(f"Found '{keyword}'")
                subtype = subtype_enum
                break
        
        if subtype == TrainerSubtype.UNKNOWN:
            return None
        
        return DetectionResult(
            card_type=CardType.TRAINER,
            confidence=0.9,
            evidence=evidence,
            trainer_subtype=subtype
        )


def detect_card_type(img: Image.Image) -> CardType:
    """Convenience function to detect card type."""
    detector = CardTypeDetector()
    result = detector.detect(img)
    return result.card_type


def detect_card_details(img: Image.Image) -> DetectionResult:
    """Get full detection result including variant."""
    detector = CardTypeDetector()
    return detector.detect(img)


if __name__ == "__main__":
    from preprocessing import preprocess_image
    
    # Test with Pokemon card
    img = preprocess_image("screenshots/test/pkm_card.png")
    detector = CardTypeDetector()
    result = detector.detect(img)
    print(f"Pokemon test card: {result.card_type.value}")
    print(f"  Variant: {result.pokemon_variant.value}")
    print(f"  Evidence: {result.evidence}")
    
    # Test with Trainer card
    img = preprocess_image("screenshots/test/pkm_trainer_card.png")
    result = detector.detect(img)
    print(f"\nTrainer test card: {result.card_type.value}")
    print(f"  Subtype: {result.trainer_subtype.value}")
    print(f"  Evidence: {result.evidence}")
