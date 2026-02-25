#!/usr/bin/env python3
"""
HP Extraction - Validate and extract HP values.
"""

import re
from dataclasses import dataclass


@dataclass
class HPExtraction:
    """Result of HP extraction."""
    value: str | None
    confidence: float
    raw_match: str


class HPExtractor:
    """Extract HP with validation against reasonable Pokemon HP range."""
    
    # Valid HP range for Pokemon cards
    MIN_HP = 30
    MAX_HP = 330
    
    # Patterns to match HP
    PATTERNS = [
        # KP: 120 or KP120
        (r'KP?\s*[:\.]?\s*(\d{2,3})', 'KP format'),
        # HP: 120
        (r'HP\s*[:\.]?\s*(\d{2,3})', 'HP format'),
        # 120 KP (number followed by KP)
        (r'(\d{2,3})\s*KP', 'number + KP'),
        # 120 HP (number followed by HP)  
        (r'(\d{2,3})\s*HP', 'number + HP'),
    ]
    
    def extract(self, text: str) -> HPExtraction:
        """
        Extract HP from OCR text.
        
        Args:
            text: OCR text from zone
            
        Returns:
            HPExtraction with value and confidence
        """
        if not text:
            return HPExtraction(None, 0.0, "")
        
        text_upper = text.upper()
        
        # Try each pattern
        for pattern, fmt in self.PATTERNS:
            match = re.search(pattern, text_upper, re.IGNORECASE)
            if match:
                hp_str = match.group(1)
                try:
                    hp_val = int(hp_str)
                    
                    # Validate HP range
                    if self.MIN_HP <= hp_val <= self.MAX_HP:
                        return HPExtraction(
                            value=str(hp_val),
                            confidence=0.9,
                            raw_match=match.group(0)
                        )
                    
                    # If out of range but looks like HP, lower confidence
                    if 10 <= hp_val <= 400:
                        return HPExtraction(
                            value=str(hp_val),
                            confidence=0.5,
                            raw_match=match.group(0)
                        )
                        
                except ValueError:
                    continue
        
        # Try to find standalone 2-3 digit numbers that might be HP
        # This is a fallback for when OCR reads "KP 12o" instead of "KP 120"
        standalone = re.findall(r'\b(\d{2,3})\b', text)
        for num_str in standalone:
            try:
                hp_val = int(num_str)
                if self.MIN_HP <= hp_val <= self.MAX_HP:
                    return HPExtraction(
                        value=str(hp_val),
                        confidence=0.4,  # Lower confidence - fallback
                        raw_match=num_str
                    )
            except ValueError:
                continue
        
        return HPExtraction(None, 0.0, "")


def extract_hp(text: str) -> str | None:
    """Convenience function to extract HP."""
    result = HPExtractor().extract(text)
    return result.value


if __name__ == "__main__":
    # Test cases
    test_cases = [
        "Endivie 60",
        "KP 120",
        "HP: 100",
        "120 KP",
        "Donphan 120",
        "KP 12o",  # OCR error
        "30 KP",
        "330 KP",
        "15 KP",  # Too low
    ]
    
    extractor = HPExtractor()
    for text in test_cases:
        result = extractor.extract(text)
        print(f"'{text}' -> HP: {result.value}, conf: {result.confidence}")
