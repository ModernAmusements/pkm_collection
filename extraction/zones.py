#!/usr/bin/env python3
"""
Zone extraction - Define and extract zones from card images.
"""

from dataclasses import dataclass
from enum import Enum
from PIL import Image


class CardType(Enum):
    """Card type enumeration."""
    POKEMON = "pokemon"
    TRAINER = "trainer"


@dataclass
class Zone:
    """Represents a zone on a card."""
    name: str
    y_start: float  # Percentage from top (0.0 - 1.0)
    y_end: float    # Percentage from top (0.0 - 1.0)
    ocr_priority: int = 0  # Higher = more important for OCR


class ZoneDefinitions:
    """Percentage-based zone definitions for 555px height cards (matching V1)."""
    
    # Pokemon card zones (matching V1 - based on 555px height)
    POKEMON = {
        'name': Zone('name', 0.00, 0.10, ocr_priority=10),
        'evolution': Zone('evolution', 0.10, 0.12, ocr_priority=1),
        'artwork': Zone('artwork', 0.12, 0.47, ocr_priority=0),
        'card_number': Zone('card_number', 0.47, 0.51, ocr_priority=8),
        'attacks': Zone('attacks', 0.51, 0.84, ocr_priority=9),
        'bottom': Zone('bottom', 0.84, 1.00, ocr_priority=5),
    }
    
    # Trainer card zones (matching V1)
    TRAINER = {
        'type': Zone('type', 0.00, 0.06, ocr_priority=5),
        'name': Zone('name', 0.06, 0.15, ocr_priority=10),
        'artwork': Zone('artwork', 0.15, 0.43, ocr_priority=0),
        'effect': Zone('effect', 0.43, 0.87, ocr_priority=9),
        'set_info': Zone('set_info', 0.87, 1.00, ocr_priority=7),
    }
    
    @classmethod
    def get_zones(cls, card_type: CardType) -> dict[str, Zone]:
        """Get zone definitions for a card type."""
        if card_type == CardType.POKEMON:
            return cls.POKEMON
        return cls.TRAINER
    
    @classmethod
    def get_ocr_zones(cls, card_type: CardType) -> list[Zone]:
        """Get zones that need OCR, sorted by priority."""
        zones = cls.get_zones(card_type)
        ocr_zones = [z for z in zones.values() if z.ocr_priority > 0]
        return sorted(ocr_zones, key=lambda z: z.ocr_priority, reverse=True)


class ZoneExtractor:
    """Extract zones from preprocessed card images."""
    
    def __init__(self, target_height: int = 1380):
        self.target_height = target_height
    
    def extract(self, img: Image.Image, zone_name: str, 
                card_type: CardType) -> Image.Image | None:
        """Extract a specific zone by name."""
        zones = ZoneDefinitions.get_zones(card_type)
        if zone_name not in zones:
            return None
        
        zone = zones[zone_name]
        return self._extract_zone(img, zone)
    
    def extract_all(self, img: Image.Image, 
                   card_type: CardType) -> dict[str, Image.Image]:
        """Extract all zones for a card type."""
        zones = ZoneDefinitions.get_zones(card_type)
        result = {}
        
        for name, zone in zones.items():
            extracted = self._extract_zone(img, zone)
            if extracted:
                result[name] = extracted
        
        return result
    
    def _extract_zone(self, img: Image.Image, zone: Zone) -> Image.Image:
        """Extract zone using percentage coordinates."""
        w, h = img.size
        
        y1 = int(zone.y_start * h)
        y2 = int(zone.y_end * h)
        
        return img.crop((0, y1, w, y2))
    
    def extract_for_ocr(self, img: Image.Image, 
                       card_type: CardType) -> dict[str, Image.Image]:
        """Extract zones optimized for OCR."""
        ocr_zones = ZoneDefinitions.get_ocr_zones(card_type)
        result = {}
        
        for zone in ocr_zones:
            extracted = self._extract_zone(img, zone)
            if extracted:
                result[zone.name] = extracted
        
        return result


def extract_zone(img: Image.Image, zone_name: str, 
                card_type: CardType) -> Image.Image | None:
    """Convenience function to extract a single zone."""
    extractor = ZoneExtractor()
    return extractor.extract(img, zone_name, card_type)


if __name__ == "__main__":
    from preprocessing import preprocess_image
    
    # Test with sample image
    img = preprocess_image("screenshots/test/pkm_card.png")
    print(f"Preprocessed: {img.size}")
    
    extractor = ZoneExtractor()
    
    # Extract Pokemon zones
    pokemon_zones = extractor.extract_all(img, CardType.POKEMON)
    print(f"\nPokemon zones extracted: {list(pokemon_zones.keys())}")
    
    for name, zone_img in pokemon_zones.items():
        print(f"  {name}: {zone_img.size}")
        zone_img.save(f"debug_zone_{name}.png")
