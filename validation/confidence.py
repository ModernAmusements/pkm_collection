#!/usr/bin/env python3
"""
Validation and confidence scoring for extracted card data.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractionResult:
    """Complete result of card extraction."""
    card_data: dict[str, Any]
    confidence: float
    missing_fields: list[str]
    warnings: list[str]
    needs_api_fallback: bool = False


@dataclass
class FieldScore:
    """Score for a single extracted field."""
    field_name: str
    present: bool
    confidence: float
    weight: float
    
    @property
    def score(self) -> float:
        return self.confidence * self.weight if self.present else 0.0


class ConfidenceScorer:
    """Calculate extraction confidence for card data."""
    
    # Field weights for confidence calculation
    FIELD_WEIGHTS = {
        'name': 30,
        'hp': 20,
        'card_number': 15,
        'energy_type': 15,
        'attacks': 10,
        'stage': 5,
        'rarity': 5,
    }
    
    # Required fields by card type
    REQUIRED_FIELDS = {
        'Pokemon': ['name', 'hp', 'card_number', 'energy_type'],
        'Trainer': ['name', 'card_number'],
    }
    
    # Confidence thresholds
    HIGH_CONFIDENCE = 75
    MEDIUM_CONFIDENCE = 50
    LOW_CONFIDENCE = 25
    
    def score(self, card_data: dict[str, Any], 
              card_type: str = 'Pokemon') -> ExtractionResult:
        """
        Calculate confidence score for extracted card data.
        
        Args:
            card_data: Dictionary of extracted card fields
            card_type: "Pokemon" or "Trainer"
            
        Returns:
            ExtractionResult with score and metadata
        """
        field_scores: list[FieldScore] = []
        missing_fields: list[str] = []
        warnings: list[str] = []
        
        # Score each field
        for field_name, weight in self.FIELD_WEIGHTS.items():
            value = card_data.get(field_name)
            present = value is not None and value != ''
            
            # Get confidence from extraction if available
            field_conf = card_data.get(f'{field_name}_confidence', 0.8 if present else 0.0)
            
            if not present and field_name in self.REQUIRED_FIELDS.get(card_type, []):
                missing_fields.append(field_name)
            
            field_scores.append(FieldScore(
                field_name=field_name,
                present=present,
                confidence=field_conf,
                weight=weight
            ))
        
        # Calculate total score
        total_score = sum(s.score for s in field_scores)
        max_possible = sum(s.weight for s in field_scores)
        
        # Normalize to 0-100
        confidence = (total_score / max_possible * 100) if max_possible > 0 else 0
        
        # Check for warnings
        if card_type == 'Pokemon':
            hp = card_data.get('hp')
            if hp:
                try:
                    hp_val = int(hp)
                    if hp_val < 30 or hp_val > 330:
                        warnings.append(f"Unusual HP value: {hp_val}")
                except ValueError:
                    warnings.append(f"Invalid HP format: {hp}")
        
        # Determine if API fallback is needed
        needs_fallback = (
            confidence < self.LOW_CONFIDENCE or 
            len(missing_fields) > 0
        )
        
        return ExtractionResult(
            card_data=card_data,
            confidence=confidence,
            missing_fields=missing_fields,
            warnings=warnings,
            needs_api_fallback=needs_fallback
        )
    
    def get_confidence_level(self, confidence: float) -> str:
        """Get human-readable confidence level."""
        if confidence >= self.HIGH_CONFIDENCE:
            return "high"
        elif confidence >= self.MEDIUM_CONFIDENCE:
            return "medium"
        elif confidence >= self.LOW_CONFIDENCE:
            return "low"
        else:
            return "very_low"


class CardValidator:
    """Validate extracted card data."""
    
    def validate(self, card_data: dict[str, Any], 
                card_type: str = 'Pokemon') -> tuple[bool, list[str]]:
        """
        Validate card data completeness and correctness.
        
        Returns:
            (is_valid, list of errors)
        """
        errors = []
        
        # Check required fields
        required = self.REQUIRED_FIELDS.get(card_type, [])
        for field in required:
            value = card_data.get(field)
            if not value or value == '':
                errors.append(f"Missing required field: {field}")
        
        # Validate HP range
        hp = card_data.get('hp')
        if hp:
            try:
                hp_val = int(hp)
                if not (30 <= hp_val <= 330):
                    errors.append(f"HP out of valid range: {hp_val}")
            except ValueError:
                errors.append(f"Invalid HP value: {hp}")
        
        # Validate card number
        card_num = card_data.get('card_number')
        if card_num:
            try:
                num_val = int(card_num)
                if not (1 <= num_val <= 500):
                    errors.append(f"Card number out of valid range: {num_val}")
            except ValueError:
                errors.append(f"Invalid card number: {card_num}")
        
        # Validate energy type
        valid_energies = {
            'Fire', 'Water', 'Lightning', 'Grass', 'Fighting',
            'Psychic', 'Darkness', 'Metal', 'Fairy', 'Dragon', 'Colorless'
        }
        energy = card_data.get('energy_type')
        if energy and energy not in valid_energies:
            errors.append(f"Invalid energy type: {energy}")
        
        return len(errors) == 0, errors


# Convenience functions
def calculate_confidence(card_data: dict[str, Any], 
                        card_type: str = 'Pokemon') -> ExtractionResult:
    """Calculate confidence for extracted card data."""
    return ConfidenceScorer().score(card_data, card_type)


def validate_card(card_data: dict[str, Any], 
                 card_type: str = 'Pokemon') -> tuple[bool, list[str]]:
    """Validate card data."""
    return CardValidator().validate(card_data, card_type)


if __name__ == "__main__":
    # Test confidence scoring
    scorer = ConfidenceScorer()
    
    # Test case 1: Good extraction
    good_data = {
        'name': 'Donphan',
        'hp': '120',
        'hp_confidence': 0.9,
        'card_number': '232',
        'card_number_confidence': 0.8,
        'energy_type': 'Fighting',
        'energy_type_confidence': 0.85,
    }
    
    result = scorer.score(good_data, 'Pokemon')
    print(f"Good data - Confidence: {result.confidence:.1f}%")
    print(f"  Level: {scorer.get_confidence_level(result.confidence)}")
    print(f"  Missing: {result.missing_fields}")
    print(f"  Needs API: {result.needs_api_fallback}")
    
    # Test case 2: Poor extraction
    poor_data = {
        'name': 'Donphan',
    }
    
    result = scorer.score(poor_data, 'Pokemon')
    print(f"\nPoor data - Confidence: {result.confidence:.1f}%")
    print(f"  Level: {scorer.get_confidence_level(result.confidence)}")
    print(f"  Missing: {result.missing_fields}")
    print(f"  Needs API: {result.needs_api_fallback}")
