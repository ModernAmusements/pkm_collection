#!/usr/bin/env python3
"""
Minimal OCR extraction for TCG Pocket cards.
Extracts only: name, stage, HP, card number (Pokedex #)
"""

import re
import pytesseract
from PIL import Image, ImageEnhance


def extract_name_and_stage(zone_img: Image.Image) -> tuple[str | None, str | None]:
    """
    Extract Pokemon name and stage from Zone 1.
    Returns: (name, stage)
    """
    # Don't preprocess - raw RGB works better for names
    text = pytesseract.image_to_string(zone_img, config='--psm 6')
    
    name = None
    stage = None
    
    # Find stage patterns (German + English)
    # OCR often reads "PHASE" as "eas=" or similar
    stage_patterns = [
        (r'PHASE\s*2', 'Phase 2'),
        (r'PHASE\s*1', 'Phase 1'),
        (r'eas=\s*1', 'Phase 1'),  # OCR error for PHASE 1
        (r'eas=\s*2', 'Phase 2'),  # OCR error for PHASE 2
        (r'Stufe\s*2', 'Stage 2'),
        (r'Stufe\s*1', 'Stage 1'),
        (r'BASIS\b', 'Basic'),
        (r'Stage\s*1', 'Stage 1'),
        (r'Stage\s*2', 'Stage 2'),
    ]
    
    text_upper = text.upper()
    for pattern, stage_val in stage_patterns:
        if re.search(pattern, text_upper, re.IGNORECASE):
            stage = stage_val
            break
    
    # Find name - look for capitalized words, skip OCR artifacts
    lines = text.strip().split('\n')[:5]
    for line in lines:
        words = line.split()
        for word in words:
            clean = ''.join(c for c in word if c.isalpha())
            # Skip OCR artifacts and short words
            if len(clean) >= 4 and clean[0].isupper() and not clean.startswith('EAS'):
                name = clean
                break
        if name:
            break
    
    return name, stage


def extract_hp(zone_img: Image.Image) -> str | None:
    """
    Extract HP from Zone 1.
    Returns: HP value as string or None
    """
    # Don't preprocess - raw works better
    text = pytesseract.image_to_string(zone_img, config='--psm 6')
    
    # German: KP 120, KP: 120, 120 KP
    # English: HP 120, HP: 120, 120 HP
    # OCR errors: "xe 120" might be read instead of "KP 120"
    patterns = [
        r'KP?\s*[:\.]?\s*(\d{2,3})',
        r'HP\s*[:\.]?\s*(\d{2,3})',
        r'(\d{2,3})\s*KP',
        r'(\d{2,3})\s*HP',
        r'[XK]\w{0,2}\s*(\d{2,3})',  # OCR error: xe 120
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            hp_val = int(match.group(1))
            if 30 <= hp_val <= 330:
                return str(hp_val)
    
    return None


def extract_pokedex_number(zone_img: Image.Image) -> str | None:
    """
    Extract Pokedex number from Zone 4 (card number area).
    Returns: Pokedex number as string or None
    """
    gray = zone_img.convert('L')
    enhancer = ImageEnhance.Contrast(gray)
    img = enhancer.enhance(2.0)
    
    text = pytesseract.image_to_string(img, config='--psm 6')
    
    # German: Nr. 232, Nr 232
    # English: No. 232, #232
    patterns = [
        r'Nr\.?\s*(\d{3})',
        r'No\.?\s*(\d{3})',
        r'#\s*(\d{3})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def minimal_ocr(img: Image.Image) -> dict:
    """
    Run minimal OCR on preprocessed card image.
    Returns dict with: name, stage, hp, pokedex_number
    """
    from extraction import ZoneExtractor, CardType
    
    extractor = ZoneExtractor()
    
    # Extract name/stage zone (Zone 1: 0-10%)
    name_zone = extractor.extract(img, 'name', CardType.POKEMON)
    
    # Extract card number zone (Zone 4: 47-51%)
    card_zone = extractor.extract(img, 'card_number', CardType.POKEMON)
    
    result = {}
    
    if name_zone:
        name, stage = extract_name_and_stage(name_zone)
        result['name'] = name
        result['stage'] = stage
        
        hp = extract_hp(name_zone)
        result['hp'] = hp
    
    if card_zone:
        pokedex = extract_pokedex_number(card_zone)
        result['pokedex_number'] = pokedex
    
    return result


if __name__ == "__main__":
    from preprocessing import preprocess_image
    
    # Test with Donphan
    img = preprocess_image("screenshots/test/pkm_card.png")
    
    result = minimal_ocr(img)
    print("Minimal OCR Result:")
    for k, v in result.items():
        print(f"  {k}: {v}")
