
#!/usr/bin/env python3
import json
import csv
import os
import sys
import shutil
from collections import Counter

MITM_PORT = 8080
CAPTURE_DIR = "./mitm_capture"
OUTPUT_JSON = "cards_full.json"
OUTPUT_CSV = "my_cards_full.csv"

def check_dependencies():
    if not shutil.which("mitmproxy"):
        print("Error: mitmproxy not found. Install with: brew install mitmproxy")
        sys.exit(1)

def extract_cards_from_flows():
    all_cards = []

    if not os.path.isdir(CAPTURE_DIR):
        print("Error: Capture directory not found.")
        sys.exit(1)

    for root, _, files in os.walk(CAPTURE_DIR):
        for fname in files:
            path = os.path.join(root, fname)
            try:
                with open(path, "rb") as f:
                    content = f.read().decode(errors="ignore")
                    if '"card_id"' in content or '"cards"' in content:
                        try:
                            j = json.loads(content)
                            cards = j.get("cards", [])
                            if not cards and "id" in j and "card_id" in j:
                                cards = [j]
                            all_cards.extend(cards)
                        except Exception:
                            continue
            except Exception:
                continue

    if not all_cards:
        print("Error: No cards found in captured flows.")
        sys.exit(1)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_cards, f, ensure_ascii=False, indent=2)

    return all_cards

def generate_csv(all_cards):
    cards_list = []
    for card in all_cards:
        name = card.get("name", "").strip()
        rarity = card.get("rarity", "")
        type_id = card.get("type", "")
        pack_id = card.get("pack_id", "")

        if name:
            cards_list.append((name, pack_id, rarity, type_id))

    print(f"Found {len(cards_list)} cards with names")

    counter = Counter(cards_list)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Card Name", "Pack ID", "Rarity", "Type ID", "Count"])
        for (name, pack_id, rarity, type_id), count in sorted(counter.items()):
            writer.writerow([name, pack_id, rarity, type_id, count])

def main():
    print("=== Pokémon TCG Pocket Full Collection Extractor ===")
    print("1. Run mitmproxy manually: mitmproxy --listen-port 8080 --save-stream mitm_capture")
    print("2. Configure your iPhone to use your Mac as proxy (Port 8080).")
    print("3. Scroll your full collection in the app.")
    input("Press ENTER once capture is complete and mitmproxy is stopped...")

    check_dependencies()
    all_cards = extract_cards_from_flows()
    generate_csv(all_cards)

    print(f"Done! Files created: {OUTPUT_JSON}, {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
