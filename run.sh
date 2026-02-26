#!/bin/bash
# Run the card extraction app (V2) - Continuous mode with set filter
cd "$(dirname "$0")"

echo "=========================================="
echo "Pokemon TCG Pocket - Card Extraction"
echo "=========================================="

# Check for available sets
echo ""
echo "Available sets in PKM_CARDS:"
if [ -d "PKM_CARDS" ]; then
    ls -1 PKM_CARDS/ 2>/dev/null | while read set; do
        count=$(ls PKM_CARDS/$set/*.png 2>/dev/null | wc -l | tr -d ' ')
        if [ "$count" -gt 0 ]; then
            echo "  $set ($count cards)"
        fi
    done
else
    echo "  No PKM_CARDS folder found"
fi

echo ""

# Ask for set (optional)
read -p "Enter set to process (or press Enter for all): " target_set

if [ -n "$target_set" ]; then
    echo "Processing set: $target_set"
    SET_FLAG="--set $target_set"
else
    SET_FLAG=""
fi

# Run extraction
echo ""
echo "[1/2] Running extraction..."
python3 extract_batch_v2.py run $SET_FLAG

# Export to CSV after capture
echo ""
echo "[2/2] Exporting to CSV..."
python3 -c "
import sys
sys.path.insert(0, '.')
from database import export_csv
export_csv()
print('Exported to collection_export.csv')
"

# Show current stats
echo ""
echo "=========================================="
echo "Current Collection Stats"
echo "=========================================="
python3 -c "
import sys
sys.path.insert(0, '.')
from database import get_stats
stats = get_stats()
print(f'Total unique cards: {stats[\"total_unique\"]}')
print(f'Total quantity: {stats[\"total_quantity\"]}')
if stats.get('by_set'):
    print('')
    print('By Set:')
    for s in stats['by_set']:
        print(f'  {s[\"set_name\"]}: {s[\"qty\"]}')
"

echo ""
echo "Done! Run again to continue capturing."
