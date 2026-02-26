# Pokémon TCG Pocket Card Inventory

Extract your complete card collection from Pokémon TCG Pocket using OCR + API matching.

## Versions

- **V2 (Recommended)**: Minimal OCR + API Match = 100% Confidence
- **V1**: Original full OCR version (deprecated)

## How It Works (V2)

**Philosophy**: Minimal OCR for name, then API match for complete data

```
1. MINIMAL OCR    → Extract only CARD NAME from image
2. API MATCH     → Find card in scraped database (name → 100% match)
3. SAVE          → Full card data from API (HP, attacks, weakness, etc.)
```

This approach gives **100% confidence** on matched cards because:
- OCR only reads the name (most reliable)
- API provides complete data (attacks, weakness, retreat, illustrator, etc.)
- No OCR errors on complex fields

## Extraction Flow (V2)

```
┌─────────────────────┐
│ 1. PREPROCESS      │ Crop screenshot to card region
│ Screenshot         │ 8.55% sides, 13.86% top, 31.64% bottom
└──────────┬──────────┘
              ▼
┌─────────────────────┐
│ 2. DETECT TYPE     │ OCR Zone 1, check for HP/KP (Pokemon) vs TRAINER
│ Pokemon/Trainer    │
└──────────┬──────────┘
              ▼
┌─────────────────────┐
│ 3. MINIMAL OCR     │ Extract ONLY the card name
│ Name only          │ No HP, no card# - just name
└──────────┬──────────┘
              ▼
┌─────────────────────┐
│ 4. API MATCH       │ Find in local Limitless database
│ Name → 100% match  │ Match by name = 100% confidence
└──────────┬──────────┘
              ▼
┌─────────────────────┐
│ 5. SAVE            │ SQLite + captured/ + cropped/
└─────────────────────┘
```

## Folder Structure

```
tcgp/
├── api/                    # API integration
│   ├── cache/            # Downloaded card data
│   │   ├── cards.json              # chase-manning JSON (2777 cards)
│   │   ├── limitless_cards.json     # English Limitless (~2111 cards)
│   │   ├── german_cards_complete.json # German cards (4834 cards)
│   │   ├── eng_to_ger_names.json    # English→German name mapping
│   │   └── expansions.json          # Set definitions
│   ├── download.py       # Download chase-manning database
│   ├── scrape_all.py     # Scrape Limitless website
│   ├── scrape_german_details.py # Scrape German details
│   ├── local_lookup.py   # Local card matching (German + English)
│   └── limitless.py      # Web scraper
│
├── preprocessing/          # Image preprocessing
│   ├── crop.py          # Crop to card region
│   └── denoise.py       # Holo card noise removal
│
├── extraction/           # Zone extraction
│   ├── zones.py         # Zone definitions (%-based)
│   └── detector.py      # Card type detection
│
├── screenshots/
│   ├── to_process/      # Input images
│   ├── captured/         # Processed originals
│   ├── cropped/         # Cropped card images
│   └── failed_to_capture/ # Failed extractions
│
├── extract_batch_v2.py   # V2 (Minimal OCR + API)
├── collection.py         # CLI for collection
└── database.py          # SQLite storage
```

## Setup

### Install Dependencies

```bash
pip install pillow pytesseract beautifulsoup4 requests
brew install tesseract
```

### Initial Setup (One Time)

```bash
# Download card database (chase-manning JSON)
python3 api/download.py

# Scrape Limitless for complete card data (attacks, weakness, etc.)
python3 api/scrape_all.py
```

### Capture Screenshots

1. Open Pokémon TCG Pocket on your phone
2. Go to your card collection
3. Take screenshots of each card
4. Transfer images to your Mac
5. Put images in `screenshots/to_process/`

## Usage

### Run Extraction

```bash
# Using run.sh (recommended - also exports CSV)
./run.sh

# Or directly with V2
python3 extract_batch_v2.py run
python3 extract_batch_v2.py run 50    # Process 50 cards

# Show status
python3 extract_batch_v2.py status

# Reset progress
python3 extract_batch_v2.py reset
```

### Collection Management

```bash
# List all cards
python3 collection.py list

# Search cards
python3 collection.py search "Pikachu"

# Show stats
python3 collection.py stats

# Export to CSV
python3 collection.py export
```

## API Data Sources

### 1. German Cards (Primary for German OCR)
- Source: `pokemongohub.net` (German)
- Contains: 4834 cards (all 14 sets)
- Fields: german_name, hp, card_number, set_id, weakness+damage, retreat, attacks, illustrator

### 2. Limitless Scraped (English)
- Source: `pocket.limitlesstcg.com`
- Contains: 2111 cards
- Fields: ALL (attacks, weakness, retreat, stage, evolution, illustrator)

### 3. Chase-manning JSON (Fallback)
- Source: `github.com/chase-manning/pokemon-tcg-pocket-cards`
- Contains: 2777 cards
- Fields: name, HP, type, set, rarity, artist

### Matching Priority
1. **German cards** - matched by German OCR name
2. **Limitless English** - for attacks and additional data
3. **Chase-manning** - fallback

### Cross-Reference Logic
When a German card is matched:
- Uses German name from OCR
- Uses English attacks from Limitless (if available)
- Uses German weakness with +damage (e.g., "Fighting+20")
- Uses German retreat when has energy type

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
    ability TEXT,
    attacks TEXT,        -- JSON
    weakness TEXT,
    resistance TEXT,
    retreat_cost TEXT,
    rarity TEXT,
    illustrator TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

## Tips

- Script saves progress automatically - safe to stop anytime
- Failed cards go to `failed_to_capture/` - can retry later
- V2 gives 100% confidence on matched cards
- Check `screenshots/cropped/` for processed card images
- CSV is auto-exported after each run via `run.sh`
