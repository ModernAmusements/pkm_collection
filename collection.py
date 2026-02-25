#!/usr/bin/env python3
"""
CLI for managing Pokémon card collection.
"""

import argparse
import sys
from database import (
    init_db,
    get_all_cards,
    search_cards,
    get_stats,
    add_card,
    remove_card,
    export_csv,
    get_failed_captures,
    clear_collection,
)


def cmd_list(args):
    """List all cards in collection."""
    cards = get_all_cards()
    
    if not cards:
        print("Collection is empty.")
        return
    
    print(f"\n{'Name':<25} {'Category':<12} {'Set':<20} {'#':<6} {'Qty':<4}")
    print("-" * 75)
    
    for card in cards:
        print(f"{card['name']:<25} {card['category'] or '-':<12} "
              f"{card['set_name'] or '-':<20} {card['card_number'] or '-':<6} "
              f"{card['quantity']:<4}")
    
    print(f"\nTotal: {len(cards)} unique cards")


def cmd_search(args):
    """Search cards by name."""
    cards = search_cards(args.query)
    
    if not cards:
        print(f"No cards found matching '{args.query}'")
        return
    
    print(f"\nFound {len(cards)} card(s):\n")
    
    for card in cards:
        print(f"  {card['name']} (x{card['quantity']})")
        if card.get('set_name'):
            print(f"    Set: {card['set_name']} #{card['card_number']}")
        if card.get('category'):
            print(f"    Category: {card['category']}")
        print()


def cmd_stats(args):
    """Show collection statistics."""
    stats = get_stats()
    
    print("\n=== Collection Statistics ===\n")
    print(f"  Unique cards:     {stats['total_unique']}")
    print(f"  Total quantity:   {stats['total_quantity']}")
    print(f"  Failed captures:  {stats['failed_count']}")
    
    if stats['by_category']:
        print("\n  By Category:")
        for cat in stats['by_category']:
            print(f"    {cat['category'] or 'Unknown'}: {cat['qty']} ({cat['count']} unique)")
    
    print()


def cmd_add(args):
    """Add a card to collection."""
    card_data = {
        'name': args.name,
        'category': args.category,
        'set': args.set,
        'card_number': args.card_number,
        'hp': args.hp,
    }
    
    add_card(card_data, args.quantity)
    print(f"Added {args.quantity}x {args.name} to collection.")


def cmd_remove(args):
    """Remove a card from collection."""
    success = remove_card(args.name, args.quantity)
    
    if success:
        print(f"Removed {args.quantity}x {args.name} from collection.")
    else:
        print(f"Card '{args.name}' not found in collection.")


def cmd_export(args):
    """Export collection to CSV."""
    success = export_csv(args.output)
    
    if success:
        print(f"Collection exported to {args.output}")
    else:
        print("No cards to export.")


def cmd_failed(args):
    """Show failed captures."""
    failed = get_failed_captures()
    
    if not failed:
        print("No failed captures.")
        return
    
    print(f"\n{len(failed)} failed capture(s):\n")
    
    for f in failed:
        print(f"  {f['filename']} - {f['created_at']}")
        if f.get('ocr_text'):
            text = f['ocr_text'][:100] + "..." if len(f['ocr_text']) > 100 else f['ocr_text']
            print(f"    OCR: {text}")
    print()


def cmd_clear(args):
    """Clear entire collection."""
    if not args.force:
        response = input("This will delete ALL cards and failed captures. Are you sure? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return
    
    clear_collection()
    print("Collection cleared.")


def main():
    parser = argparse.ArgumentParser(description="Pokémon Card Collection Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # list
    subparsers.add_parser("list", help="List all cards")
    
    # search
    search_parser = subparsers.add_parser("search", help="Search cards by name")
    search_parser.add_argument("query", help="Search term")
    
    # stats
    subparsers.add_parser("stats", help="Show collection statistics")
    
    # add
    add_parser = subparsers.add_parser("add", help="Add card to collection")
    add_parser.add_argument("name", help="Card name")
    add_parser.add_argument("--category", "-c", default="", help="Card category")
    add_parser.add_argument("--set", "-s", default="", help="Set name")
    add_parser.add_argument("--number", "-n", dest="card_number", default="", help="Card number")
    add_parser.add_argument("--hp", default="", help="HP")
    add_parser.add_argument("--quantity", "-q", type=int, default=1, help="Quantity")
    
    # remove
    remove_parser = subparsers.add_parser("remove", help="Remove card from collection")
    remove_parser.add_argument("name", help="Card name")
    remove_parser.add_argument("--quantity", "-q", type=int, default=1, help="Quantity to remove")
    
    # export
    export_parser = subparsers.add_parser("export", help="Export to CSV")
    export_parser.add_argument("--output", "-o", default="collection_export.csv", help="Output file")
    
    # failed
    subparsers.add_parser("failed", help="Show failed captures")
    
    # clear
    clear_parser = subparsers.add_parser("clear", help="Clear collection")
    clear_parser.add_argument("--force", "-f", action="store_true", help="Skip confirmation")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize database
    init_db()
    
    # Dispatch
    commands = {
        "list": cmd_list,
        "search": cmd_search,
        "stats": cmd_stats,
        "add": cmd_add,
        "remove": cmd_remove,
        "export": cmd_export,
        "failed": cmd_failed,
        "clear": cmd_clear,
    }
    
    commands[args.command](args)


if __name__ == "__main__":
    main()
