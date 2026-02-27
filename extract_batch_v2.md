# extract_batch_v2.py - Line by Line Documentation

## Overview

This is the **main extraction script** for capturing Pokemon TCG Pocket cards from screenshots. It uses EasyOCR + API matching to achieve high confidence card identification.

**File**: `extract_batch_v2.py`  
**Lines**: ~670  
**Purpose**: Process card images → Extract signals via OCR → Match against database → Save to collection

---

## Current Workflow (Actual)

```
1. EASYOCR: Extract multiple signals (name, HP, attacks, weakness, retreat)
2. CROSS-REFERENCE: Match against german_cards_complete.json
3. CONFIDENCE CHECK: 
   - >=60% -> Save to collection.db + captured folder + processed list
   - <60% -> Move to failed_to_capture/ (NOT added to processed list - reprocessable)
4. SAVE: Only high-confidence cards added to processed list

Input Folders:
- PKM_CARDS/{SET}/ (organized by set - PRIORITIZED)
- screenshots/to_process/ (fallback)
```

---

## Section 1: Imports & Configuration (Lines 1-35)

### Lines 1-23: Module Docstring
```python
#!/usr/bin/env python3
"""
Pokemon TCG Pocket Card Extractor - V2
EasyOCR + API Match = High Confidence

Workflow:
1. EASYOCR: Extract multiple signals (name, HP, attacks, weakness, retreat)
2. CROSS-REFERENCE: Match against german_cards_complete.json
3. CONFIDENCE CHECK: 
   - >=60% -> Save to collection.db + captured folder + processed list
   - <60% -> Move to failed_to_capture/ (NOT added to processed list - reprocessable)
4. SAVE: Only high-confidence cards added to processed list

Input Folders:
- screenshots/to_process/ (fallback)
- PKM_CARDS/{SET}/ (organized by set, prioritized)
"""
```
- Shebang for Python 3 execution
- Documentation explaining the V2 workflow

### Lines 13-22: Standard Library Imports
```python
import os
import re
import glob
import sys
import json
import time
from PIL import Image
import pytesseract
import easyocr
```
- `os, re, glob, sys, json, time` - File system, regex, file matching, CLI, JSON, timing
- `PIL.Image` - Image processing
- `pytesseract` - Tesseract OCR for text extraction
- `easyocr` - EasyOCR (better for German text)

### Lines 23-32: Project Imports
```python
from preprocessing import CardCropper, preprocess_image
from extraction import (
    CardType, 
    ZoneExtractor, 
    detect_card_type, 
    DetectionResult
)
import database
from api.local_lookup import lookup_card, load_cards
from PIL import ImageEnhance
```
- `preprocessing/` - Image cropping and preprocessing
- `extraction/` - Zone extraction and card type detection
- `database` - SQLite operations
- `api.local_lookup` - Card matching against German database

---

## Section 2: Helper Functions (Lines 35-180)

### Lines 35-88: `correct_hp_ocr()` - HP OCR Error Correction
```python
def correct_hp_ocr(hp_str: str) -> int | None:
    """
    Correct common OCR errors in HP values.
    Examples: 502→50, 802→80, 0→8, 52→50, 58→50
    """
```
Corrects common OCR misreads on HP values:
1. **Direct conversion** - Try `int(hp_str)` if 20-340
2. **Strip trailing zeros** - `502` → `50`, `802` → `80`
3. **Fix common digits** - `52`→`50`, `58`→`50`
4. **First digit only** - `5` → `50` as fallback

### Lines 91-104: `enhance_for_ocr()` - Image Enhancement
```python
def enhance_for_ocr(img: Image.Image) -> Image.Image:
    """
    Enhance image for better OCR results.
    Increases contrast and applies gamma correction.
    """
    # Increase contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.3)
    
    # Slight sharpness
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.2)
    
    return img
```
Boosts contrast by 1.3x and sharpness by 1.2x for better OCR accuracy.

### Lines 107-115: `get_easyocr_reader()` - Lazy OCR Reader
```python
# EasyOCR reader (lazy init)
_easyocr_reader = None

def get_easyocr_reader():
    """Get or create EasyOCR reader."""
    global _easyocr_reader
    if _easyocr_reader is None:
        _easyocr_reader = easyocr.Reader(['de', 'en'], gpu=True)
    return _easyocr_reader
```
Lazy initialization of EasyOCR reader (German + English, GPU enabled).

### Lines 118-180: `easyocr_extract()` - Extract Multiple Signals
```python
def easyocr_extract(img: Image.Image) -> dict:
    """Extract card signals using EasyOCR. Format: 'TUSKA KP 60' or 'BASIS PIKACHU KP 60'"""
```
Extracts from card image:
- **name**: Word before "KP" (German HP)
- **hp**: Number after "KP"
- **attacks**: Pattern matching (word + damage)
- **weakness**: German "Schwäche" + type + damage
- **retreat**: German "Rückzug" + number
- **pokedex**: "Nr." + number

---

## Section 3: Constants (Lines 183-189)

```python
SCREENSHOT_DIR = "screenshots/to_process"
PKM_CARDS_DIR = "PKM_CARDS"  # Folder with set subdirectories (e.g., PKM_CARDS/B1/)
CAPTURED_DIR = "screenshots/captured"
CROPPED_DIR = "screenshots/cropped"
FAILED_DIR = "screenshots/failed_to_capture"
PROGRESS_FILE = "extraction_progress.json"
BATCH_SIZE = 25
```

| Constant | Purpose |
|----------|---------|
| `SCREENSHOT_DIR` | Input images (screenshots) |
| `PKM_CARDS_DIR` | Alternative input (organized by set) |
| `CAPTURED_DIR` | Successfully processed images |
| `CROPPED_DIR` | Cropped card images |
| `FAILED_DIR` | Failed extraction images |
| `PROGRESS_FILE` | JSON tracking processed files |
| `BATCH_SIZE` | Default batch size (25) |

---

## Section 4: Progress Functions (Lines 192-224)

### Lines 192-212: `get_all_images()` - Find All Input Images
```python
def get_all_images():
    """Get all images from both to_process and PKM_CARDS/*/ folders."""
```
1. First checks `PKM_CARDS/` subdirectories (organized by set)
2. Then checks `screenshots/to_process/` fallback
3. Returns list of tuples: `(filepath, set_name)`

### Lines 215-219: `load_progress()` - Load Progress File
```python
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'processed': [], 'failed': [], 'last_index': -1}
```
Loads tracking JSON with processed/failed file lists.

### Lines 222-224: `save_progress()` - Save Progress
```python
def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)
```
Saves updated progress after each card.

---

## Section 5: OCR Functions (Lines 227-311)

### Lines 227-300: `minimal_ocr_name()` - Alternative OCR for Name Only
```python
def minimal_ocr_name(img: Image.Image, card_type: CardType) -> str | None:
    """
    MINIMAL OCR: Extract only the card NAME.
    This is all we need to match against the API database.
    
    Tries multiple zones as fallback for full art cards.
    """
```
**Strategy**:
1. Try name zone with multiple PSM modes (6, 4, 11)
2. Skip common OCR artifacts (EAS, THE, AND, etc.)
3. Fallback: full image OCR for full-art cards

### Lines 303-311: `enhanced_ocr_extract()` - EasyOCR Multi-Signal Extraction
```python
def enhanced_ocr_extract(img: Image.Image, card_type: CardType) -> dict:
    """
    ENHANCED OCR: Extract multiple signals from the card using EasyOCR.
    EasyOCR is much better than Tesseract for German text.
    """
    signals = easyocr_extract(img)
    signals['set_id'] = None
    signals['card_number'] = None
    return signals
```
Wrapper around `easyocr_extract()` that adds set/card_number placeholders.

---

## Section 6: Matching Functions (Lines 314-379)

### Lines 314-344: `match_with_api()` - Match OCR Name to Database
```python
def match_with_api(ocr_name: str, card_type: str, target_set: str = None) -> tuple[dict | None, float]:
    """
    Match OCR name with API database.
    Returns: (matched_card_data, confidence)
    
    If name matches EXACTLY → 100% confidence
    If name matches FUZZY → 90% confidence  
    If name matches CLOSEST → 80% confidence
    If no match → None, 0%
    """
```
Matches OCR name against local database with confidence scoring.

### Lines 347-379: `card_to_dict()` - Convert CardData to Dict
```python
def card_to_dict(card) -> dict:
    """Convert API CardData to dict for database."""
```
Converts API `CardData` object to dictionary format:
- Extracts attacks list
- Formats weakness with damage calculation
- Maps all fields for SQLite storage

---

## Section 7: Main Processing (Lines 382-537)

### Lines 382-508: `process_card_v2()` - Process Single Card
```python
def process_card_v2(image_path: str, target_set: str = None) -> tuple[bool, dict | None]:
    """
    Process a single card using EasyOCR + Multi-Signal API Match.
    
    Extraction signals:
    1. Name (OCR)
    2. HP (parse from text)
    3. Attack names (OCR)
    4. Weakness (energy type + damage)
    5. Retreat cost
    """
```

**5-Step Process**:

| Step | Function | Description |
|------|----------|-------------|
| 1 | Preprocess | Crop card, convert to greyscale |
| 2 | Detect Type | Pokemon vs Trainer |
| 3 | OCR | Extract name, HP, attacks via EasyOCR |
| 4 | Match | Cross-reference with german_cards_complete.json |
| 5 | Save | Add to database, move to captured/ |

**High Confidence Flow** (≥60%):
- Save to collection.db
- Save cropped image to `screenshots/cropped/`
- Move original to `screenshots/captured/`
- Return `True`

**Low Confidence Flow** (<60%):
- Move to `screenshots/failed_to_capture/`
- Do NOT add to processed list
- Return `False`

### Lines 511-536: `add_to_collection()` - Save to Database
```python
def add_to_collection(card_data: dict):
    """Add card to SQLite database."""
```
Prepares card data and calls `database.add_card()` to save to SQLite.

---

## Section 8: Batch Processing (Lines 539-612)

### Lines 539-612: `run_batch_v2()` - Process Multiple Cards
```python
def run_batch_v2(start_index=0, batch_size=BATCH_SIZE, target_set=None):
```
Processes a batch of cards:

1. Load progress (processed/failed files)
2. Get all images from input folders
3. Filter by set if specified
4. Exclude already processed and failed files
5. For each card:
   - Call `process_card_v2()`
   - Update progress file after each
   - Sleep 0.3s between cards
6. Print summary statistics

---

## Section 9: CLI Functions (Lines 615-670)

### Lines 615-629: `show_status()` - Display Status
```python
def show_status():
    progress = load_progress()
    to_proc = len(glob.glob(...))
    captured = len(glob.glob(...))
    failed = len(glob.glob(...))
    
    print status summary
```
Shows: cards to process, captured, failed.

### Lines 632-670: `main()` - CLI Entry Point
```python
def main():
    os.makedirs(...)  # Create output directories
    
    if len(sys.argv) == 1:
        show_status()
        print usage
        return
    
    cmd = sys.argv[1]
    
    # Check for --set flag
    if '--set' in sys.argv:
        target_set = sys.argv[sys.argv.index('--set') + 1]
    
    if cmd == 'status':
        show_status()
    elif cmd == 'reset':
        remove PROGRESS_FILE
    elif cmd == 'run':
        load progress, start at last_index + 1
        run_batch_v2(...)
```

**CLI Commands**:

| Command | Description |
|---------|-------------|
| `python3 extract_batch_v2.py` | Show status |
| `python3 extract_batch_v2.py status` | Show status |
| `python3 extract_batch_v2.py run` | Process all (25 at a time) |
| `python3 extract_batch_v2.py run 50` | Process 50 cards |
| `python3 extract_batch_v2.py run --set B1` | Process specific set |
| `python3 extract_batch_v2.py reset` | Clear progress |

---

## Data Flow Diagram

```
Input Image
    │
    ▼
preprocess_image() ──▶ Crop + Greyscale
    │
    ▼
detect_card_type() ──▶ Pokemon or Trainer
    │
    ▼
enhanced_ocr_extract() ──▶ EasyOCR signals
    │
    ▼
lookup_card() ──▶ Match in german_cards_complete.json
    │
    ├──▶ CONFIDENCE ≥ 60% ──▶ database.add_card() ──▶ collection.db
    │                              └──▶ screenshots/captured/
    │
    └──▶ CONFIDENCE < 60% ──▶ screenshots/failed_to_capture/
                                └── NOT added to processed list
```

---

## Key Design Decisions

1. **EasyOCR**: Extract multiple signals (name, HP, attacks, weakness, retreat) using EasyOCR
2. **High Confidence Threshold**: Only save cards with ≥60% confidence
3. **Failed Cards Reprocessable**: Low confidence cards go to failed folder, NOT to processed list
4. **Progress Tracking**: JSON file tracks processed/failed for resume capability
5. **Batch Processing**: Process 25 cards at a time with 0.3s delay
6. **PKM_CARDS Priority**: Check PKM_CARDS/{SET}/ folders first, then to_process/
