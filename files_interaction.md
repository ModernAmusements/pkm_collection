# Files & Directory Structure

## Root Directory Files

| File | Size | Purpose |
|------|------|---------|
| **DOCS.md** | 11KB | Consolidated project documentation |
| **README.md** | 9KB | Original quick reference guide |
| **extract_batch_v2.py** | 24KB | Main extraction script - Processes card images via OCR + API matching |

### extract_batch_v2.py - Main Extraction Script

This is the **main card extraction script**. It takes card screenshots and identifies them using OCR + API matching.

**Workflow:**
1. **MINIMAL OCR**: Extract only NAME from card image
2. **API MATCH**: Find card by OCR name in german_cards_complete.json
3. **VERIFY**: If name matches → high confidence, use ALL API data
4. **SAVE**: Store complete card data from API (not OCR) to collection.db

**Usage:**

```bash
# Process all images in screenshots/to_process/
python3 extract_batch_v2.py run

# Process specific number of images
python3 extract_batch_v2.py run 50

# Process specific set only
python3 extract_batch_v2.py run --set B1

# Reset progress (start over)
python3 extract_batch_v2.py reset

# Show status
python3 extract_batch_v2.py status
```

**How it works:**

1. Load images from `screenshots/to_process/`
2. Preprocess (crop card, convert to greyscale)
3. Detect card type (Pokemon vs Trainer)
4. Extract name via OCR (Tesseract/EasyOCR)
5. Match name against `german_cards_complete.json`
6. Save matched card to `collection.db`
7. Move processed image to `screenshots/captured/`

**Key Functions:**

| Function | Description |
|----------|-------------|
| `preprocess_image()` | Crop card, convert to greyscale |
| `detect_card_type()` | Detect Pokemon vs Trainer |
| `minimal_ocr_name()` | Extract card name via OCR |
| `enhanced_ocr_extract()` | Extract multiple signals using EasyOCR |
| `match_by_signals()` | Match OCR signals against database |
| `process_card_v2()` | Process single card |
| `load_progress()` / `save_progress()` | Track extraction progress |

**Dependencies:**
- `preprocessing/` - Image preprocessing
- `extraction/` - Zone extraction
- `api/local_lookup.py` - Card matching
- `database.py` - Save to collection.db
| **collection.py** | 5KB | CLI tool - Command-line interface to query/manage your collection.db |

### collection.py - CLI Commands

This is a command-line tool to interact with your collection.db. It provides commands to view, search, add, remove cards and export data.

```bash
# View all cards in collection
python3 collection.py list

# Search for specific card
python3 collection.py search "Pikachu"

# Show collection statistics
python3 collection.py stats

# Add a card manually
python3 collection.py add "Pikachu" --set A1 --number 45 --hp 60

# Remove a card
python3 collection.py remove "Pikachu"

# Export collection to CSV
python3 collection.py export --output my_cards.csv

# Clear entire collection
python3 collection.py clear --force
```

| Command | Description |
|---------|-------------|
| `list` | Display all cards in collection |
| `search` | Search cards by name |
| `stats` | Show collection statistics |
| `add` | Manually add a card |
| `remove` | Remove a card |
| `export` | Export to CSV file |
| `clear` | Delete all cards |
| **database.py** | 7KB | SQLite module - Low-level database functions (used by collection.py and extract_batch_v2.py) |

### database.py - Core SQLite Functions

This is the **low-level SQLite module** that handles all database operations. It provides the core functions that both `collection.py` (CLI) and `extract_batch_v2.py` use to interact with `collection.db`.

**Key Functions:**

| Function | Description |
|----------|-------------|
| `get_db()` | Connect to SQLite database |
| `init_db()` | Initialize database schema (creates tables) |
| `add_card()` | Add card to collection (or increment quantity if exists) |
| `remove_card()` | Remove card or decrement quantity |
| `get_all_cards()` | Get all cards in collection |
| `search_cards()` | Search by name, category, or set |
| `get_stats()` | Get collection statistics |
| `add_failed_capture()` | Record failed OCR attempts |
| `get_failed_captures()` | Get all failed captures |
| `export_csv()` | Export collection to CSV file |
| `clear_collection()` | Delete all cards and failed captures |

**Database Tables:**

1. **cards** - Main collection table with all card data
2. **failed_captures** - Tracks failed OCR attempts for debugging

**Used by:**
- `collection.py` - CLI interface
- `extract_batch_v2.py` - Extraction script
| **run.sh** | 2KB | Shell script - Quick start wrapper for extraction + export |
| **collection.db** | 20KB | SQLite database - Your personal captured card collection |
| **extraction_progress.json** | 0KB | Progress file - Tracks processed images |
| **csv/** | Folder | CSV exports |
| **csv/personal/** | Subfolder | Your personal collection exports (from extraction) |
| **csv/personal/*.csv** | Future | Export your collection.csv here after extraction |
| **csv/reference/** | Subfolder | Reference databases |
| **csv/reference/german_cards.csv** | (was german_cards_all.csv) | German card database (2,520 cards) |

## File Interactions - How Everything Works Together

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                    USER ACTION                        │
                    │   python3 extract_batch_v2.py run                      │
                    └─────────────────────┬───────────────────────────────┘
                                          │
                                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            extract_batch_v2.py                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ preprocessing/│──▶│  extraction/ │──▶│ api/local_   │──▶│ database.py │  │
│  │              │    │              │    │ lookup.py    │    │              │  │
│  │ Crop +       │    │ Detect type │    │ Match name   │    │ Add card to │  │
│  │ enhance img  │    │ Extract zone│    │ to DB        │    │ collection.db│  │
│  └─────────────┘    └─────────────┘    └──────────────┘    └──────┬───────┘  │
└────────────────────────────────────────────────────────────────────│─────────┘
                                                                       │
                       ┌───────────────────────────────────────────────┘
                       ▼
              ┌──────────────────┐
              │  collection.db  │
              │  (SQLite)       │
              └────────┬─────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│collection.py│  │screenshots/ │  │csv/personal/│
│ (CLI)       │  │ captured/   │  │collection.csv│
└─────────────┘  └─────────────┘  └─────────────┘
```

### Data Flow

**1. Extraction Process:**
```
screenshots/to_process/ (input images)
         │
         ▼
extract_batch_v2.py
         │
         ├─▶ preprocessing/ (crop, enhance)
         │
         ├─▶ extraction/ (detect type, extract zones)
         │
         ├─▶ api/local_lookup.py (match against german_cards_complete.json)
         │
         ├─▶ database.py (add_card)
         │
         ▼
collection.db (saved cards)
```

**2. Query Process:**
```
User runs: python3 collection.py list
         │
         ▼
collection.py
         │
         ▼
database.py (get_all_cards)
         │
         ▼
collection.db
         │
         ▼
Display cards to user
```

**3. Export Process:**
```
User runs: python3 collection.py export
         │
         ▼
collection.py
         │
         ▼
database.py (export_csv)
         │
         ▼
csv/personal/collection.csv (or custom filename)
```

### File Dependencies

| File | Depends On | Used By |
|------|------------|---------|
| `extract_batch_v2.py` | preprocessing/, extraction/, api/local_lookup.py, database.py | User directly |
| `collection.py` | database.py | User directly |
| `database.py` | collection.db | collection.py, extract_batch_v2.py |
| `api/local_lookup.py` | api/cache/german_cards_complete.json | extract_batch_v2.py |
| `run.sh` | extract_batch_v2.py, collection.py, database.py | User (wrapper) |

### Key Interactions

1. **extract_batch_v2.py** → uses **preprocessing/** + **extraction/** + **api/local_lookup.py** + **database.py**
2. **api/local_lookup.py** → reads **api/cache/german_cards_complete.json** (card database)
3. **database.py** → reads/writes **collection.db**
4. **collection.py** → uses **database.py** to query **collection.db**
5. **run.sh** → wraps **extract_batch_v2.py** + **collection.py** + **database.py**

### API Cache Interaction

```
german_cards_complete.json (reference data)
         ▲
         │
         │ (read by)
         │
api/local_lookup.py
         │
         │ (used by)
         │
extract_batch_v2.py
```

| Folder | Purpose |
|--------|---------|
| `api/` | Card database API & local lookup |
| `screenshots/` | Input/output images (to_process, captured, cropped, failed) |
| `preprocessing/` | Image preprocessing (crop, enhance) |
| `extraction/` | Zone extraction definitions |
| `ocr_engine/` | OCR utilities |
| `validation/` | Validation scripts |
| `docs/` | Documentation (currently empty) |
| `venv/` | Python virtual environment |

## Key Executables

```bash
# Main extraction
python3 extract_batch_v2.py run

# View collection
python3 collection.py list

# Quick start wrapper
./run.sh

# Other collection commands
python3 collection.py search "Pikachu"   # Search cards
python3 collection.py stats              # Show statistics
python3 collection.py export             # Export to CSV
```

## Screenshots Subfolders

| Folder | Purpose |
|--------|---------|
| `screenshots/to_process/` | Add your card images here for processing |
| `screenshots/captured/` | Processed originals (saved after extraction) |
| `screenshots/cropped/` | Cropped card images |
| `screenshots/debug/` | Debug zone images |
| `screenshots/failed_to_capture/` | Failed extractions |

## API Cache Files

Located in `api/cache/`:

| File | Description |
|------|-------------|
| `german_cards_complete.json` | Main German card database (2,777+ cards) |
| `eng_to_ger_names.json` | English to German name mapping |
| `name_mapping_complete.json` | Set+number to German name mapping |
| `expansions.json` | Set/expansion information |
| `set_mapping.json` | English to German set names |

## Database Schema

### collection.db - Your Personal Collection

This is your **personal card collection database**. When you run `extract_batch_v2.py`, matched cards are saved here.

**What it stores:**
- Card name, HP, set, card number
- Attacks, weakness, retreat cost
- Quantity (if you have duplicates)
- Timestamps (created_at, updated_at)

**Related files:**
- `collection.py` - CLI tool to query/manage this database
- `csv/personal/collection.csv` - CSV export of this database
- Screenshots are saved to `screenshots/captured/` when cards are added

**Usage:**
```bash
python3 collection.py list              # View all cards
python3 collection.py search "Pikachu"  # Search cards
python3 collection.py stats             # Show statistics
python3 collection.py export            # Export to CSV
```

### cards table

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
    regulation_mark TEXT,
    rarity TEXT,
    illustrator TEXT,
    effect TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(name, set_name, card_number)
)
```

### failed_captures table

```sql
failed_captures (
    id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    ocr_text TEXT,
    created_at TIMESTAMP
)
```
