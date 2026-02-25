#!/usr/bin/env python3
"""
Data models for API responses.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CardData:
    """Complete card data from API."""
    # Basic info
    id: str                           # e.g., "a2a-038"
    name: str                         # e.g., "Donphan"
    hp: Optional[int] = None          # e.g., 120
    energy_type: str = ""              # e.g., "Fighting"
    
    # Evolution
    stage: str = ""                   # e.g., "Stage 1", "Basic"
    evolution_from: str = ""           # e.g., "Phanpy"
    
    # Card info
    card_number: str = ""             # e.g., "38"
    set_id: str = ""                  # e.g., "a2a"
    set_name: str = ""                # e.g., "Triumphant Light"
    rarity: str = ""                  # e.g., "◊◊"
    
    # Attacks
    attacks: list = None              # List of attack dicts
    
    # Other
    weakness: str = ""                # e.g., "Grass"
    retreat: int = 0                  # e.g., 3
    illustrator: str = ""             # e.g., "Shin Nagasawa"
    flavor_text: str = ""             # e.g., Pokédex entry
    
    # Metadata
    api_source: str = ""              # 'local' or 'limitless'
    pokedex_number: Optional[int] = None  # e.g., 232
    
    def __post_init__(self):
        if self.attacks is None:
            self.attacks = []


@dataclass
class OCRResult:
    """Minimal OCR result for matching."""
    name: str = ""
    hp: str = ""
    energy_type: str = ""
    pokedex_number: str = ""          # e.g., "232" from "Nr. 232"
    language: str = "de"              # 'de' or 'en'
    raw_text: str = ""                # Full raw OCR text


@dataclass
class MatchResult:
    """Result of matching OCR to API."""
    success: bool
    card: Optional[CardData] = None
    match_type: str = ""              # 'exact', 'fuzzy', 'closest', 'none'
    confidence: float = 0.0
    errors: list = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
