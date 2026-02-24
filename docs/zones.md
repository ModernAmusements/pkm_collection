# Pokemon TCG Pocket - Zone Extraction Documentation

## Overview

The extraction process divides card screenshots into **zones** for OCR processing. Each zone contains specific card information based on the card structure.

## Image Preprocessing

```
Here’s a clear flow diagram of the corrected pipeline with scaling and per-zone OCR:

⸻


Original Image (raw capture)
            │
            ▼
 Crop Card Region (percentages of original)  ←– Relative to original dimensions
            │
            ▼
 Scale Card Crop to 1380px height  ←– Normalizes all cards to same size
            │
            ▼
 Cut Zones of Interest (percentages of normalized crop)
   ┌──────────────┬──────────────┬──────────────┐
   │ Name Zone    │ HP / Type    │ Attacks Zone │ … 
   └──────────────┴──────────────┴──────────────┘
            │
            ▼
 Run OCR per Zone → Extract Text
            │
            ▼
 Combine OCR Results → Structured Data
            │
            ▼
 Check Completeness:
 ┌───────────────┐
 │ All info?     │
 │   Yes → CSV   │
 │   No → Query  │
 │       API     │
 └───────────────┘
            │
            ▼
 Save Final Data → CSV
            │
            ▼
 Save Card Crop → /captured Folder


⸻

Key Points:
	•	Crop → Scale → Cut Zones: ensures all OCR zones have uniform pixel size.
	•	OCR per zone: improves accuracy vs full-card OCR.
	•	API fallback: fills missing info automatically.
	•	CSV + captured folder: structured storage of data + images.

⸻



```

---

## Pokemon Card Zones

Based on pokemon_rules.md, Pokemon cards are divided into:

- **Zone 1**: Top Bar - Basis/Phase1/2 Name + HP + Stage indicator (Basic/Stage 1/Stage 2/ex)
- **Zone 2**: Evolution Info - Evolution details
- **Zone 3**: Artwork Box - Large central illustration
- **Zone 4**: Card Number - Set number + rarity symbol
- **Zone 5**: Attacks Section - Energy cost + Attack name + Damage + Effect
- **Zone 6**: Bottom Info Bar - Weakness + Resistance + Retreat + Regulation mark

### OCR Zones (Pokemon)
- **Zone 1**: Primary identification - Extract for OCR
- **Zone 4**: Card number - Extract for OCR
- **Zone 5**: Attacks - Extract for OCR

---

## Trainer Card Zones

Based on pokemon_rules.md, Trainer cards are divided into:

- **Zone 1**: Top Label - Trainer + subtype (Item / Supporter / Stadium)
- **Zone 2**: Name - Card name
- **Zone 3**: Artwork - Full artwork
- **Zone 4**: Effect Text - Card effect description
- **Zone 5**: Set Info - Set details

### OCR Zones (Trainer)
- **Zone 2**: Name - Extract for OCR
- **Zone 4**: Effect Text - Extract for OCR

---

## Card Type Detection Flow

1. Extract Zone 1 from preprocessed image
2. Check for "HP/KP" keywords → Pokemon card
3. Check for "TRAINER/ARTIKEL/STADION" keywords → Trainer card

---

## Workflow

1. **Preprocess**: Crop screenshot → Scale to 1380px height
2. **Detect Card Type**: Check Zone 1 for keywords
3. **OCR Zones**: Extract relevant zones for each card type
4. **Search API**: Match OCR text to card database
5. **Save**: Move to captured + append to CSV

---

## Summary

### Pokemon OCR Zones
- Zone 1: Top Bar (Name+HP+Stage)
- Zone 4: Card Number
- Zone 5: Attacks

### Trainer OCR Zones
- Zone 2: Name
- Zone 4: Effect Text

### API Usage
- Last resort - OCR is primary method
- Use to fill missing card details after OCR extraction
