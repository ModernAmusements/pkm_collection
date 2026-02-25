# Pokemon TCG Pocket - Zone Extraction Documentation

## Overview

The extraction process uses **Minimal OCR + API Match** to achieve 100% confidence. Zones are used only for extracting the card name.

## Image Preprocessing

```
Original Image (1170x2532)
            │
            ▼
   Crop Card Region (percentages)
   - Left/Right: 8.55%
   - Top: 13.86%
   - Bottom: 31.64%
            │
            ▼
   Output: 970x1381
            │
            ▼
   Zone 1 Extraction (Name only)
            │
            ▼
   OCR: Extract card name
            │
            ▼
   API Match: Find in database
            │
            ▼
   Save: Full card data from API
```

## Card Type Detection

1. Extract Zone 1 from preprocessed image
2. Check for "HP/KP" keywords → Pokemon card
3. Check for "TRAINER/ITEM" keywords → Trainer card

## Zone Definitions

### Pokemon Card Zones

| Zone | % Range | Content | Used in V2 |
|------|---------|---------|-------------|
| 1 | 0-10% | Name + HP + Energy | **YES** (Name only) |
| 2 | 10-12% | Evolution info | No |
| 3 | 12-47% | Artwork | No |
| 4 | 47-51% | Card number + Rarity | No |
| 5 | 51-84% | Attacks + Abilities | No |
| 6 | 84-100% | Weakness + Resistance + Retreat | No |

### Trainer Card Zones

| Zone | % Range | Content | Used in V2 |
|------|---------|---------|-------------|
| 1 | 0-6% | Type label (Item/Stadium) | No |
| 2 | 6-15% | Card name | **YES** (Name only) |
| 3 | 15-43% | Artwork | No |
| 4 | 43-87% | Effect text | No |
| 5 | 87-100% | Set info | No |

## V2 Architecture

```
┌─────────────────────────────────────────┐
│ preprocessing/crop.py                    │
│ - Crop sides (8.55%)                   │
│ - Crop height (13.86% top, 31.64% bot)│
└─────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────┐
│ extraction/detector.py                  │
│ - Card type detection                   │
└─────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────┐
│ extraction/zones.py                     │
│ - ZoneExtractor                         │
│ - Extract Zone 1 (name)                 │
└─────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────┐
│ pytesseract                             │
│ - OCR Zone 1                            │
│ - Extract card name only                │
└─────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────┐
│ api/local_lookup.py                     │
│ - Match name in Limitless data          │
│ - Return full card data                 │
└─────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────┐
│ database.py                             │
│ - Save to SQLite                       │
│ - Export to CSV                        │
└─────────────────────────────────────────┘
```

## Why Minimal OCR?

1. **Name is most reliable**: OCR reads names accurately
2. **API has complete data**: Attacks, weakness, retreat, etc. from scraped database
3. **100% confidence**: Name match = complete data

## API Data Sources

### Limitless Scraped Data (Primary)
- Source: `pocket.limitlesstcg.com`
- Contains: Full card data
  - HP, Stage, Evolution
  - Attacks (name, damage)
  - Weakness, Retreat
  - Illustrator, Rarity
  - Energy type

### chase-manning JSON (Fallback)
- Source: `github.com/chase-manning/pokemon-tcg-pocket-cards`
- Contains: 2777 cards
  - Basic card info

## Workflow

1. **Preprocess**: Crop screenshot → 970x1381
2. **Detect Type**: Check Zone 1 for keywords
3. **Minimal OCR**: Extract ONLY name from Zone 1
4. **API Match**: Find card in local database
5. **Save**: Full card data from API → SQLite

## Output Folders

- `screenshots/to_process/` - Input images
- `screenshots/captured/` - Processed originals
- `screenshots/cropped/` - Cropped card images
- `screenshots/failed_to_capture/` - Failed extractions
