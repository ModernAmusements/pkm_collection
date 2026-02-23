# Pokémon TCG Pocket Card Inventory

Extract your complete card collection from Pokémon TCG Pocket using OCR + API.

## How It Works

1. **Capture screenshots** of your cards in the game
2. **OCR** extracts card names from images
3. **API** fetches full German card data
4. **CSV output** with all card details

## Folder Structure

```
screenshots/
├── to_process/          # Screenshots to process (input)
├── captured/           # Successfully identified cards (output)
└── failed_to_capture/  # Cards that couldn't be identified (output)
```

## Setup

### Install Dependencies

```bash
pip install pillow pytesseract requests
brew install tesseract
```

### Capture Screenshots

1. Open Pokémon TCG Pocket on your phone
2. Go to your card collection
3. Screen record or take screenshots of each card
4. Transfer images to your Mac
5. Put images in `screenshots/to_process/`

## Usage

### Process Cards (Batch Mode)

```bash
# Show status
python3 extract_batch.py status

# Process next 25 cards
python3 extract_batch.py run

# Process specific number
python3 extract_batch.py run 50

# Generate CSV from captured cards
python3 extract_batch.py csv

# Reset progress
python3 extract_batch.py reset
```

### Workflow

1. Add new screenshots to `screenshots/to_process/`
2. Run `python3 extract_batch.py run` to process batches
3. Script pauses after each batch - safe to stop anytime
4. Run again to continue from where you left off
5. When done, run `python3 extract_batch.py csv`

## Output CSV Format

| Column | Description |
|--------|-------------|
| Card Name | German card name |
| HP | Hit points (KP) |
| Energy Type | Card energy (Feuer, Wasser, Psycho, etc.) |
| Weakness | Weakness type and value |
| Retreat Cost | Retreat cost |
| Ability Name | German ability name |
| Ability Description | Ability effect |
| Attack 1 Name | First attack name |
| Attack 1 Cost | Energy cost |
| Attack 1 Damage | Damage |
| Attack 1 Description | Attack effect |
| Attack 2 Name | Second attack name |
| Attack 2 Cost | Energy cost |
| Attack 2 Damage | Damage |
| Attack 2 Description | Attack effect |
| Rarity | Rareza (Ein Diamant, Zwei Diamant, etc.) |
| Pack | German set name |

## Card Data Source

Card data fetched from [TCGdex API](https://tcgdex.dev/) in German.

## Card Layouts

### Pokemon Cards
- Zone 1 (0-55px): Phase + Name + KP + Energy
- Zone 2 (55-65px): Evolution
- Zone 3 (65-263px): Artwork
- Zone 4 (263-282px): Card Number
- Zone 5 (282-475px): Attacks & Abilities
- Zone 6 (475-494px): Weakness + Retreat

### Trainer Cards
- Zone 1 (0-41px): Card Type (Item, Stadium, etc.)
- Zone 2 (41-81px): Name
- Zone 3 (81-289px): Artwork
- Zone 4 (289-480px): Effect text
- Zone 5 (480-554px): Special trainer rule

## Image Preprocessing

- Crop sides: 8.5% from each side
- Crop height: 555px from top (14% from top)
- Scale: 3x for OCR

## Tips

- Script automatically detects Pokemon vs Trainer cards
- Process in batches of 25 to avoid API rate limits
- Use screen recording for faster capture
- Failed cards go to `failed_to_capture/` - can retry later
- Script saves progress automatically - safe to stop anytime
