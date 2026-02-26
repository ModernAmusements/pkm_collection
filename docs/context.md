# Context - Pokémon TCG Pocket Card Extractor

## Project Overview

A Python tool that extracts card data from Pokémon TCG Pocket screenshots using OCR + API matching.

## Current Version

**V2** - Minimal OCR + API Match = High Confidence

## Architecture

```
Screenshots (to_process/)
    │
    ▼
extract_batch_v2.py
    │
    ├─▶ preprocess_image() ──▶ Crop card, convert greyscale
    │
    ├─▶ detect_card_type() ──▶ Pokemon vs Trainer
    │
    ├─▶ enhanced_ocr_extract()
    │   │
    │   ├─▶ ZoneExtractor.extract() for name zone
    │   ├─▶ enhance_for_ocr() - contrast + sharpness
    │   ├─▶ pytesseract with PSM 6, 3
    │   └─▶ correct_hp_ocr() - fix OCR errors
    │
    ├─▶ api.local_lookup.match_by_signals()
    │   │
    │   └─▶ lookup_card() - fuzzy match in German DB
    │
    ├─▶ database.add_card() - SQLite
    │
    └─▶ Save image to screenshots/captured/
```

## Key Components

| Component | Purpose |
|-----------|---------|
| `extract_batch_v2.py` | Main extraction script |
| `preprocessing/crop.py` | Card cropping |
| `extraction/zones.py` | Zone definitions |
| `api/local_lookup.py` | Card matching |
| `api/cache/german_cards_complete.json` | 2,777 cards |

## OCR Pipeline

1. **Greyscale** - Convert to L mode
2. **Enhance** - Contrast 1.3x, Sharpness 1.2x
3. **PSM modes** - Try 6, then 3
4. **HP Correction** - Fix 502→50, 52→50, etc.

## Database

- **German cards**: 2,777 cards (scraped from pokemongohub.net)
- **Collection**: SQLite at `collection.db`
- **Progress**: JSON at `extraction_progress.json`

## Debug

- `screenshots/debug/` - Zone images
- `screenshots/debug/zones_enhanced/` - Enhanced zones

## Usage

```bash
# Extract all cards
python3 extract_batch_v2.py run

# Extract with set filter
python3 extract_batch_v2.py run --set B1

# View collection
python3 collection.py list

# Reset progress
python3 extract_batch_v2.py reset
```

## Known Issues

- Some OCR errors on low-quality images
- HP correction may not catch all variations
- German card names needed for matching

## Recent Fixes

- Added greyscale conversion for better OCR
- Added image enhancement (contrast/sharpness)
- Added multiple PSM mode retry
- Added HP error correction
- Fixed confidence threshold (0.9 instead of 1.0)
