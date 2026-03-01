# Project Context

## What is this?

A Pokemon TCG Pocket card extraction tool that uses OCR to scan card screenshots and automatically add them to a collection database.

## Current State

- ✅ Card extraction pipeline working
- ✅ OCR → matching → database flow functional
- ✅ German card database scraped (~2541 cards)
- ✅ Abilities scraped (~124 unique)
- ✅ Card images scraped (~2020)
- ✅ First card added to collection (Ledyba)

## What We've Built

### Data Collection (Scraping)
- `api/scrapers/scrape_pokewiki.py` - Scrapes card data from pokewiki.de
- `api/scrapers/scrape_abilities.py` - Scrapes Pokemon abilities
- Data saved to `api/cache/pokewiki_scraped_all.json`

### Core Extraction
- `extract_batch_v2.py` - Main extraction script
- `preprocessing/` - Image preprocessing
- `extraction/` - Card type detection

### Database
- `database.py` - SQLite collection management
- `collection.db` - User's card collection
- `api/cache/cards.db` - Fast lookup DB

### Matching
- `api/local_lookup.py` - Card matching logic with multiple strategies

## Key Files

| File | Purpose |
|------|---------|
| `README.md` | Project overview and usage |
| `data_workflow.md` | Data flow diagrams (mermaid) |
| `api/cache/pokewiki_scraped_all.json` | Card database (German, ~2541 cards) |
| `api/cache/card_images.json` | Card image URLs |
| `api/cache/abilities.json` | Pokemon abilities |
| `collection.db` | User's collection |

## Sets in Database

A1, A1a, A2, A2a, A2b, A3, A3a, A3b, A4, A4a, A4b, B1, B1a, B2, B2a, PROMO-A, PROMO-B

## How to Use

```bash
# Add cards to collection
./run.sh
# Or
python3 extract_batch_v2.py run

# Check collection
python3 -c "from database import get_stats; print(get_stats())"
```

## Commands Used

```bash
# Run extraction
python3 extract_batch_v2.py run --set A1

# Export to CSV
python3 -c "from database import export_csv; export_csv()"
```

## Notes

- User collects German cards only
- Never merge sets until user says "go"
- Primary data source: pokewiki.de (German wiki)
- Card matching uses multiple signals: name, HP, attacks, weakness, retreat
