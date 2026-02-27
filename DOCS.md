# Pokemon TCG Pocket Card Inventory

Extract your complete card collection from Pokemon TCG Pocket using OCR + API matching.

---

## 1. Project Overview

A Python tool that extracts card data from Pokemon TCG Pocket screenshots using OCR + API matching.

### Current Version

**V2 (Recommended)** - Minimal OCR + API Match = High Confidence

### Why Minimal OCR + API?

Traditional OCR struggles with:
- Holographic cards (sparkle patterns)
- Small fonts in badges
- German/English mixed text
- Color energy symbols

**Solution**: Extract only the name (most reliable), then get complete data from API.

---

## 2. Quick Start

```bash
# 1. Add card screenshots to folder
cp your_cards/*.png screenshots/to_process/

# 2. Run extraction
python3 extract_batch_v2.py run

# 3. View your collection
python3 collection.py list
```

### Commands

```bash
# Extraction
python3 extract_batch_v2.py run          # Process all images
python3 extract_batch_v2.py run 50      # Process 50 images
python3 extract_batch_v2.py run --set B1 # Process specific set
python3 extract_batch_v2.py reset       # Reset progress
python3 extract_batch_v2.py status       # Show status

# Collection
python3 collection.py list               # List all cards
python3 collection.py search "Pikachu"  # Search cards
python3 collection.py stats              # Show statistics
python3 collection.py export             # Export to CSV
```

---

## 3. Architecture & Data Flow

```
Screenshots (to_process/)
    │
    ▼
extract_batch_v2.py
    │
    ├─▶ preprocess_image() ──▶ Crop card,
    │
    ├─▶ detect convert greyscale_card_type() ──▶ Pokemon vs Trainer
    │
    ├─▶ easyocr_extract()
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

### Key Components

| Component | Purpose |
|-----------|---------|
| `extract_batch_v2.py` | Main extraction script |
| `preprocessing/crop.py` | Card cropping |
| `extraction/zones.py` | Zone definitions |
| `api/local_lookup.py` | Card matching |
| `api/cache/german_cards_complete.json` | 2,777+ cards |

### Project Structure

```
tcgp/
├── api/
│   ├── cache/
│   │   ├── german_cards_complete.json  # German card database
│   │   ├── eng_to_ger_names.json       # Name translations
│   │   └── name_mapping_complete.json  # Set+number to name
│   ├── local_lookup.py                 # Card matching
│   └── scrape_missing_german.py        # Update card database
│
├── screenshots/
│   ├── to_process/    # Add your card images here
│   ├── captured/      # Processed originals
│   ├── cropped/       # Cropped card images
│   └── failed_to_capture/  # Failed extractions
│
├── docs/              # Documentation (deprecated - see DOCS.md)
├── extraction/        # Zone extraction
├── ocr_engine/        # OCR utilities
├── preprocessing/     # Image preprocessing
├── validation/        # Validation scripts
│
├── extract_batch_v2.py    # Main extraction script
├── collection.py          # Collection management
├── collection.db         # Your card collection
└── run.sh                # Quick start script
```

---

## 4. OCR Pipeline

### Steps

1. **Preprocess**: Crop to card region, convert to greyscale (L mode)
2. **Enhance**: Contrast 1.3x, Sharpness 1.2x
3. **Zone Extract**: Extract name zone using ZoneExtractor
4. **OCR**: Tesseract with PSM modes 6, then 3
5. **HP Correction**: Fix common OCR errors:
   - `502` → `50`, `802` → `80` (trailing zeros)
   - `52` → `50`, `58` → `50` (wrong digit)

### Image Preprocessing

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
```

### Signals Extracted

| Signal | Source | Example |
|--------|--------|---------|
| `name` | Name zone OCR | "Schaloko" |
| `hp` | Name zone OCR | "80" |
| `attacks` | Attacks zone OCR | ["Kopfnuss", "Hartner"] |
| `weakness` | Full image OCR | "Fire+20" |
| `retreat` | Full image OCR | "3" |
| `set_id` | **From DB only** | "B1" |

---

## 5. Zone Extraction

### Card Type Detection

1. Extract Zone 1 from preprocessed image
2. Check for "HP/KP" keywords → Pokemon card
3. Check for "TRAINER/ITEM" keywords → Trainer card

### Pokemon Card Zones (970x1381 after crop)

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

---

## 6. Card Types

### Pokemon Card Variants

| Type | Layout Characteristics |
|------|----------------------|
| **Regular Pokemon** | Colored frame matching type, HP top right, Evolution box top left, Attacks centered mid-lower |
| **ex Pokemon** | Prominent "ex" next to name, Rule Box at bottom, Higher HP, Silver borders (SV era) |
| **Tera Pokemon ex** | Crystal crown icon, Sparkling fractured foil pattern, Tera rule clause added |
| **Full Art Pokemon** | Artwork covers entire card, Text boxes float above art, Heavy texture foil |
| **Illustration Rare** | Border retained, Large scenic artwork, Minimal attack area emphasis |
| **Gold / Hyper Rare** | Monochrome gold palette, Heavy texture, Same structural layout as base |

### Trainer Card Types

| Type | Description |
|------|-------------|
| **Item (Artikel)** | Fast, one-time effects. Can be played freely during your turn. Examples: Potion, Switch, Rare Candy |
| **Supporter (Unterstützung)** | Powerful one-per-turn. You may play only 1 Supporter per turn. Examples: Professor's Research, Boss's Orders |
| **Stadium (Stadion)** | Global field effects. Only one Stadium can be in play at a time. |

### Key Modern Design Shifts (Scarlet & Violet Era)

1. Silver borders (instead of yellow)
2. Cleaner typography
3. Larger HP numbers
4. Reduced shadowing/gradient
5. More art-forward rare tiers

---

## 7. Database

### German Card Database

**Source**: pokemongohub.net (German)

| Field | Coverage |
|-------|----------|
| Card name (German) | 100% |
| HP | 100% |
| Energy type | 100% |
| Stage | ~82% |
| Evolution | ~36% |
| Weakness | ~21% |
| Retreat cost | ~80% |
| Attacks (name, damage, cost) | ~66% |
| Rarity | ~100% |
| Illustrator | 100% |

**Total**: 2,777+ cards across sets A1, A1a, A2, A2a, A2b, A3, A3a, A3b, A4, A4a, A4b, PROMO-A, PROMO-B, B1

### Database Files

| File | Description |
|------|-------------|
| `api/cache/german_cards_complete.json` | Main German card database |
| `api/cache/eng_to_ger_names.json` | English to German name mapping |
| `api/cache/name_mapping_complete.json` | Set+number to German name |
| `collection.db` | User's captured cards |
| `extraction_progress.json` | Extraction progress |

### Collection Schema (SQLite)

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

---

## 8. API / Lookup System

### Matching Priority

1. **Name + Set** → Exact match (highest)
2. **Name + HP** → All sets
3. **Name + HP + Attack** → Multi-signal
4. **Name + Weak + Retreat** → No HP
5. **HP + Attack** → Low confidence
6. **HP only** → Last resort

### Confidence Levels

| Match Type | Confidence |
|------------|------------|
| Exact name + Set | 95-100% |
| Exact name + HP | 90% |
| Fuzzy name + HP | 85% |
| HP + Attack | 40-70% |
| HP only | <50% |

### Anti-False Positive Rules

- ❌ Name only → **FAIL** (no HP, no set from DB)
- ✅ Name + HP → Match (set from DB)
- ✅ Name + Set → Match (set from DB)

---

## 9. Troubleshooting / Debugging

### Debug Commands

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
```

### Debug Folders

- `screenshots/debug/` - Zone images
- `screenshots/debug/zones_enhanced/` - Enhanced zones for comparison

### Common OCR Errors

| OCR Error | Fix Applied |
|-----------|-------------|
| `502` → `50` | Trailing zeros removed |
| `802` → `80` | Trailing zeros removed |
| `52` → `50` | Wrong digit corrected |
| `xe` → (removed) | False "ex" detection |
| `EAS` → (skipped) | OCR artifact |

### Known Issues

- Some OCR errors on low-quality images
- HP correction may not catch all variations
- German card names required for matching
- Full Art cards have text overlaid on artwork - difficult for OCR

### Reset Progress

```bash
rm extraction_progress.json
```

---

## 10. Pokemon TCG Rules

### Pokemon Card Structure

1. **Top Bar**: Name, HP, Stage indicator, Evolution info
2. **Artwork Box**: Large central illustration
3. **Type + Ability**: Energy type symbol, Ability section
4. **Attacks Section**: Energy cost, Attack name, Damage, Effect
5. **Bottom Info Bar**: Weakness, Resistance, Retreat cost, Regulation mark, Set number, Rarity, Illustrator

### When a Card is Knocked Out

- Regular Pokemon: Opponent takes 1 Prize card
- Pokemon ex: Opponent takes 2 Prize cards

### Energy Types

- Colorless, Fire, Water, Grass, Electric, Psychic, Fighting, Darkness, Metal, Dragon, Fairy

### Retreat Cost

- Pokemon can retreat by discarding energy cards equal to retreat cost
- Higher retreat = harder to switch out

### Weakness

- Pokemon have a weakness to a specific energy type
- Damage shown is multiplied (typically 2x for regular, 1x for ex)
- Format in DB: "Fire+20"

---

## Update History

- Consolidated from multiple .md files into single DOCS.md
- German database is primary source (no longer uses Limitless)
- V2 extraction uses minimal OCR + API matching for 100% confidence
