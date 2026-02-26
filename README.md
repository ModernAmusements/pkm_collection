# Pokémon TCG Pocket Card Inventory

Extract your complete card collection from Pokémon TCG Pocket using OCR + API matching.

## Versions

- **V2 (Recommended)**: Minimal OCR + API Match = 100% Confidence
- **V1**: Original full OCR version (deprecated)

## Quick Start

```bash
# 1. Add card screenshots to folder
cp your_cards/*.png screenshots/to_process/

# 2. Run extraction
python3 extract_batch_v2.py run

# 3. View your collection
python3 collection.py list
```

## Debugging

```bash
# Extract zones for debugging (saved to screenshots/debug/)
python3 -c "
from PIL import Image
from extraction.zones import ZoneExtractor, CardType
from extract_batch_v2 import preprocess_image, enhance_for_ocr

img = preprocess_image('path/to/image.png')
extractor = ZoneExtractor()
zones = extractor.extract_all(img.convert('L'), CardType.POKEMON)
for name, zone in zones.items():
    zone.save(f'screenshots/debug/{name}.png')
    enhance_for_ocr(zone).save(f'screenshots/debug/{name}_enhanced.png')
"

## Project Structure

```
tcgp/
├── api/
│   ├── cache/
│   │   ├── german_cards_complete.json  # German card database (2,777 cards)
│   │   ├── eng_to_ger_names.json       # Name translations
│   │   └── name_mapping_complete.json   # Set+number to name mapping
│   ├── local_lookup.py                  # Card matching
│   └── scrape_missing_german.py         # Update card database
│
├── screenshots/
│   ├── to_process/    # Add your card images here
│   ├── captured/      # Processed originals
│   ├── cropped/       # Cropped card images
│   └── failed_to_capture/  # Failed extractions
│
├── docs/                   # Documentation
├── extraction/             # Zone extraction
├── ocr_engine/            # OCR utilities
├── preprocessing/         # Image preprocessing
├── validation/            # Validation scripts
│
├── extract_batch_v2.py    # Main extraction script
├── collection.py          # Collection management
├── collection.db         # Your card collection
└── run.sh                # Quick start script
```

## Data Flow

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Screenshot  │───▶│ Preprocess   │───▶│ Zone OCR    │───▶│ API Match   │───▶│   SQLite     │
│              │    │ Crop+Grey    │    │ Name+HP     │    │ 90-100%     │    │   Database   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                                        │
                                                                                        ▼
                                                                              ┌──────────────┐
                                                                              │   Images     │
                                                                              │ captured/    │
                                                                              └──────────────┘
```

### Detailed Flow

1. **Input**: Screenshots from Pokémon TCG Pocket
2. **Preprocess**: Crop to card region, convert to greyscale
3. **Zone OCR**: Extract name + HP from name zone (enhanced + multi-PSM)
4. **API Match**: Find card in German database by name
5. **Output**: Save to SQLite + copy image to captured/

## Extraction (V2)

```
┌─────────────────────┐
│ 1. PREPROCESS      │ Crop to card region + greyscale
└──────────┬──────────┘
              ▼
┌─────────────────────┐
│ 2. DETECT TYPE     │ Pokemon vs Trainer
└──────────┬──────────┘
              ▼
┌─────────────────────┐
│ 3. ZONE OCR        │ Extract name + HP from name zone
│ - Greyscale        │
│ - Image enhance    │
│ - Multi-PSM retry  │
│ - HP error correct │
└──────────┬──────────┘
              ▼
┌─────────────────────┐
│ 4. API MATCH       │ Find in German database
│ 90-100% confidence │
└──────────┬──────────┘
              ▼
┌─────────────────────┐
│ 5. SAVE            │ SQLite + image files
└─────────────────────┘
```

### OCR Improvements

- **Greyscale conversion** - Better OCR accuracy than RGB
- **Image enhancement** - Contrast 1.3x + Sharpness 1.2x
- **Multiple PSM modes** - Tries 6, 3, 4, 11 in sequence
- **HP correction** - Fixes common OCR errors:
  - `502` → `50`, `802` → `80` (trailing zeros)
  - `52` → `50`, `58` → `50` (wrong digit)

## German Card Database

**Source**: pokemongohub.net (scraped)

| Field | Coverage |
|-------|----------|
| Card name (German) | 100% |
| HP | 100% |
| Energy type | 100% |
| Stage | 82% |
| Evolution | 36% |
| Weakness | 21% |
| Retreat cost | 80% |
| Attacks (name, damage, cost) | 66% |
| Rarity | ~100% |
| Illustrator | 100% |
| Image URL | 0% |

**Total**: 2,520 cards (2,343 Pokemon + 177 Trainer/Item)

## Commands

### Extraction
```bash
python3 extract_batch_v2.py run          # Process all images
python3 extract_batch_v2.py run 50        # Process 50 images
python3 extract_batch_v2.py reset         # Reset progress
python3 extract_batch_v2.py status        # Show status
```

### Collection
```bash
python3 collection.py list               # List all cards
python3 collection.py search "Pikachu"   # Search cards
python3 collection.py stats              # Show statistics
python3 collection.py export             # Export to CSV
```

### Update Database
```bash
python3 api/scrape_missing_german.py    # Update German card database
```

## Database Schema

```sql
cards (
    id INTEGER PRIMARY KEY,
    name TEXT,
    category TEXT,
    quantity INTEGER,
    set_name TEXT,
    card_number TEXT,
    hp TEXT,
    stage TEXT,
    energy_type TEXT,
    evolution_from TEXT,
    attacks TEXT,        -- JSON
    weakness TEXT,
    retreat_cost TEXT,
    rarity TEXT,
    illustrator TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

## Tips

- Failed cards are saved for manual review
- Progress is saved automatically - safe to stop anytime
- Check `screenshots/cropped/` for processed images
- Check `screenshots/debug/` for OCR zone debugging
- Run `scrape_missing_german.py` periodically to update card database


1. German pokemongohub.net has all card data including attack costs in English (energy icons like eng-psychic.png, eng-fire.png)
2. URL naming bug: Card URLs like /de/card/pikachu-ex only extracted last part as name ("ex"), fixed by extracting everything after first -
3. German DB: 2,520 cards (more than official 1,689 because includes variations/EX versions)
4. We deleted limitless_cards.json - German DB is now the primary/only source
5. Created name mappings:
   - eng_to_ger_names.json (710 entries) - English name → German name
   - name_mapping_complete.json (2,520 entries) - set+number → German name
6. Cleaned German names - removed prefixes (mega, alola, galar, paldea, ur, y, x)
7. Updated code to remove all limitless references
8. Game8.co - User wants to scrape from here, but:
   - No API available
   - Doesn't have detailed card data (HP, attacks, costs) - just set overviews
   - Better alternatives: TCGdex API, chase-manning GitHub
Accomplished
Completed:
- ✅ Created german_cards_complete.json - 2,520 German cards
- ✅ Created all_cards.csv - CSV export
- ✅ Created name mappings (eng_to_ger and ger_to_eng)
- ✅ Cleaned German names (removed mega, alola, galar, paldea, ur prefixes)
- ✅ Deleted limitless_cards.json (no longer needed)
- ✅ Updated local_lookup.py - removed limitless references
- ✅ Updated extract_batch_v2.py - removed limitless import
- ✅ Updated README.md - removed limitless references
- ✅ Updated docs/my_knowledge.md - updated documentation
- ✅ Updated scrape_missing_german.py - removed limitless fallback
- ✅ Verified database and CSV are in sync
Still to do:
- Potentially scrape new sets from game8 or use TCGdex API/chase-manning GitHub
Relevant Files / Directories
Core files being worked on:
- api/cache/german_cards_complete.json - Main German card database (2,520 cards)
- api/cache/all_cards.csv - CSV export of German cards
- api/cache/eng_to_ger_names.json - English to German name mapping
- api/cache/name_mapping_complete.json - Complete set+number to German name mapping
- api/local_lookup.py - Card matching (updated to German-only)
- extract_batch_v2.py - Main extraction script (updated)
- README.md - Project documentation (updated)
- docs/my_knowledge.md - Knowledge base (updated)
Deleted:
- api/cache/limitless_cards.json - No longer needed
Current Status
- German JSON: 2,520 cards complete
- CSV: 2,520 cards in sync
- Mapping: 2,520 entries
- All code updated to remove limitless references
- Testing verified working
