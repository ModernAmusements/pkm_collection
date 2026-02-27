# Step 3: EasyOCR Extraction

## Input
- **Image**: `step_1_crop/cropped.png`
- **Card Type**: Pokemon (from Step 2)

## Process
`easyocr_extract()` function uses EasyOCR to extract multiple signals from the card:
- Name (word before "KP")
- HP (number after "KP")
- Attacks (pattern: word + number)
- Weakness (German "Schwäche")
- Retreat (German "Rückzug")
- Pokédex number

## Output (Extracted Signals)

```json
{
  "name": "IGASTARNISH",
  "hp": "90",
  "attacks": ["Nietenranke 60"],
  "weakness": null,
  "retreat": null,
  "pokedex_number": "0651"
}
```

## EasyOCR Raw Output
```
PHASE Igastarnish KP 90 Entwickel sich aus Igamaro Nr. 0651 Spitzpanzer-Pokemon Größe: 0,7 m Gewicht...
```

## Analysis

| Signal | Extracted | Expected | Status |
|--------|-----------|----------|--------|
| Name | IGASTARNISH | IGASTARNISH | ✓ CORRECT |
| HP | 90 | 90 | ✓ CORRECT |
| Attacks | Nietenranke 60 | - | ✓ |
| Weakness | null | Fire+20? | ✗ MISSING |
| Retreat | null | - | ✗ MISSING |
| Pokédex | 0651 | - | ✓ |

## Notes
- Name extraction worked correctly (found "Igastarnish" before "KP")
- Weakness and Retreat were not extracted - regex may need adjustment
- The raw EasyOCR shows "® +20" which should be weakness

## Next Step
Cross-reference extracted name with german_cards_complete.json database
