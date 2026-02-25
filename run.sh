#!/bin/bash
# Run the card extraction app (V2)
cd "$(dirname "$0")"

# Run extraction with V2
python3 extract_batch_v2.py run

# Export to CSV after capture
python3 -c "
from database import export_csv
export_csv()
print('Exported to collection_export.csv')
"
