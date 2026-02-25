#!/usr/bin/env python3
"""
Database module for card collection.
SQLite-based storage with quantity tracking.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = "collection.db"


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database with schema."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Main cards table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            quantity INTEGER DEFAULT 1,
            set_name TEXT,
            card_number TEXT,
            hp TEXT,
            stage TEXT,
            energy_type TEXT,
            evolution_from TEXT,
            ability TEXT,
            attacks TEXT,
            weakness TEXT,
            resistance TEXT,
            retreat_cost TEXT,
            regulation_mark TEXT,
            rarity TEXT,
            illustrator TEXT,
            effect TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, set_name, card_number)
        )
    """)
    
    # Failed captures table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS failed_captures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            ocr_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


def add_card(card_data: dict, quantity: int = 1):
    """
    Add card to collection.
    If card exists, increment quantity.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    import json
    
    attacks_json = None
    if card_data.get('attacks'):
        attacks_json = json.dumps(card_data['attacks']) if isinstance(card_data['attacks'], list) else card_data['attacks']
    
    cursor.execute("""
        INSERT INTO cards (name, category, quantity, set_name, card_number, hp, stage,
                         energy_type, evolution_from, ability, attacks, weakness, 
                         resistance, retreat_cost, regulation_mark, rarity, illustrator,
                         effect, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name, set_name, card_number) DO UPDATE SET
            quantity = quantity + excluded.quantity,
            updated_at = excluded.updated_at
    """, (
        card_data.get('name', ''),
        card_data.get('category', ''),
        quantity,
        card_data.get('set', ''),
        card_data.get('card_number', ''),
        card_data.get('hp', ''),
        card_data.get('stage', ''),
        card_data.get('energy_type', ''),
        card_data.get('evolution_from', ''),
        card_data.get('ability', ''),
        attacks_json,
        card_data.get('weakness', ''),
        card_data.get('resistance', ''),
        card_data.get('retreat_cost', ''),
        card_data.get('regulation_mark', ''),
        card_data.get('rarity', ''),
        card_data.get('illustrator', ''),
        card_data.get('effect', ''),
        datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()


def remove_card(name: str, quantity: int = 1) -> bool:
    """
    Remove card from collection.
    If quantity > 0, decrement quantity.
    If quantity reaches 0, delete card.
    Returns True if card was removed/decremented.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Get current quantity
    cursor.execute("SELECT quantity FROM cards WHERE name = ?", (name,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return False
    
    current_qty = row['quantity']
    
    if quantity >= current_qty:
        # Delete the card
        cursor.execute("DELETE FROM cards WHERE name = ?", (name,))
    else:
        # Decrement quantity
        cursor.execute("UPDATE cards SET quantity = quantity - ?, updated_at = ? WHERE name = ?",
                      (quantity, datetime.now().isoformat(), name))
    
    conn.commit()
    conn.close()
    return True


def get_all_cards():
    """Get all cards in collection."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cards ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def search_cards(query: str):
    """Search cards by name or category."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM cards 
        WHERE name LIKE ? OR category LIKE ? OR set_name LIKE ?
        ORDER BY name
    """, (f"%{query}%", f"%{query}%", f"%{query}%"))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_stats():
    """Get collection statistics."""
    conn = get_db()
    cursor = conn.cursor()
    
    stats = {}
    
    # Total cards
    cursor.execute("SELECT COUNT(*) as total, SUM(quantity) as total_qty FROM cards")
    row = cursor.fetchone()
    stats['total_unique'] = row['total'] or 0
    stats['total_quantity'] = row['total_qty'] or 0
    
    # By category
    cursor.execute("""
        SELECT category, COUNT(*) as count, SUM(quantity) as qty 
        FROM cards GROUP BY category
    """)
    stats['by_category'] = [dict(row) for row in cursor.fetchall()]
    
    # Failed captures
    cursor.execute("SELECT COUNT(*) FROM failed_captures")
    stats['failed_count'] = cursor.fetchone()[0]
    
    conn.close()
    return stats


def add_failed_capture(filename: str, ocr_text: str = ""):
    """Record a failed capture attempt."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO failed_captures (filename, ocr_text)
        VALUES (?, ?)
    """, (filename, ocr_text))
    conn.commit()
    conn.close()


def get_failed_captures():
    """Get all failed captures."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM failed_captures ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def export_csv(filename: str = "collection_export.csv"):
    """Export collection to CSV."""
    import csv
    cards = get_all_cards()
    
    if not cards:
        return False
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=cards[0].keys())
        writer.writeheader()
        writer.writerows(cards)
    
    return True


def clear_collection():
    """Clear all cards and failed captures."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cards")
    cursor.execute("DELETE FROM failed_captures")
    conn.commit()
    conn.close()


# Initialize on import
init_db()
