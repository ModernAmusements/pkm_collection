# Step 2: Detect Card Type

## Input
- **Image**: `step_1_crop/cropped.png`
- **Size**: 970 x 1381 pixels

## Process
`detect_card_type()` function:
- Analyzes the top portion of the card
- Looks for keywords to determine if Pokemon or Trainer
- Pokemon keywords: "KP" (German HP), "ENTWICKELT", "BASIS", "PHASE"
- Trainer keywords: "TRAINER", "ARTIKEL", "UNTERSTÜTZUNG", "STADION"

## Output
- **Card Type**: Pokemon
- **Value**: pokemon

## Detection Logic
```python
# Pokemon detection (from code)
pokemon_keywords = {"KP", "ENTWICKELT", "ENTWICKELT SICH", "BASIS", "PHASE"}

# Trainer detection
trainer_keywords = {"TRAINER", "ARTIKEL", "UNTERSTÜTZUNG", "STADION"}
```

## Notes
- This card was correctly identified as Pokemon
- Next step: EasyOCR to extract name, HP, attacks, etc.
