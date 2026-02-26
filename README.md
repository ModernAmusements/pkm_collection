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

## Project Structure

```
tcgp/
├── api/
│   ├── cache/
│   │   ├── german_cards_complete.json  # German card database (2,520 cards)
│   │   ├── eng_to_ger_names.json     # Name translations
│   │   └── name_mapping_complete.json # Set+number to name mapping
│   ├── local_lookup.py               # Card matching (German DB)
│   └── scrape_missing_german.py       # Update card database
│
├── screenshots/
│   ├── to_process/    # Add your card images here
│   ├── captured/      # Processed originals
│   └── cropped/      # Cropped card images
│
├── extract_batch_v2.py   # Main extraction script
├── collection.py         # Collection management
└── collection.db         # Your card collection
```

## Data Flow

```
Screenshot → Preprocess → OCR (Name) → Match in German DB → Save to collection.db
```

## Extraction (V2)

```
┌─────────────────────┐
│ 1. PREPROCESS      │ Crop to card region
└──────────┬──────────┘
             ▼
┌─────────────────────┐
│ 2. DETECT TYPE    │ Pokemon vs Trainer
└──────────┬──────────┘
             ▼
┌─────────────────────┐
│ 3. MINIMAL OCR     │ Extract card name only
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
- Run `scrape_missing_german.py` periodically to update card database
