#!/usr/bin/env python3
"""
Card Number Extraction - Extract set and card number.
"""

import re
from dataclasses import dataclass


@dataclass
class CardNumberExtraction:
    """Result of card number extraction."""
    card_number: str | None
    confidence: float
    raw_match: str


class CardNumberExtractor:
    """Extract card number from OCR text."""
    
    # Patterns for card numbers
    PATTERNS = [
        # Nr. 123 or Nr 123
        (r'Nr\.?\s*(\d+)', 'Nr. format'),
        # 123/198 (set size)
        (r'(\d+)\s*/\s*\d+', 'set size format'),
        # ¥123 or ¥ 123
        (r'[¥$€]\s*(\d+)', 'symbol format'),
        # Standalone number
        (r'\b(\d{1,3})\b', 'standalone'),
    ]
    
    def extract(self, text: str) -> CardNumberExtraction:
        """
        Extract card number from OCR text.
        
        Args:
            text: OCR text from card number zone
            
        Returns:
            CardNumberExtraction with value and confidence
        """
        if not text:
            return CardNumberExtraction(None, 0.0, "")
        
        # Try each pattern in order of specificity
        for pattern, fmt in self.PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                num_str = match.group(1)
                
                # Validate it's a reasonable card number (1-500)
                try:
                    num = int(num_str)
                    if 1 <= num <= 500:
                        confidence = 0.9 if fmt != 'standalone' else 0.6
                        return CardNumberExtraction(
                            card_number=num_str,
                            confidence=confidence,
                            raw_match=match.group(0)
                        )
                except ValueError:
                    continue
        
        return CardNumberExtraction(None, 0.0, "")


def extract_card_number(text: str) -> str | None:
    """Convenience function to extract card number."""
    result = CardNumberExtractor().extract(text)
    return result.card_number


if __name__ == "__main__":
    # Test cases
    test_cases = [
        "Nr. 123",
        "Nr 232",
        "123/198",
        "¥45",
        "Card 67",
        "67",
        "232",
    ]
    
    extractor = CardNumberExtractor()
    for text in test_cases:
        result = extractor.extract(text)
        print(f"'{text}' -> {result.card_number}, conf: {result.confidence}")
