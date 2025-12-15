"""
Query pairing events from the database.
"""
import os
import sys
import sqlite3

# Force path so imports always work
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app.db import DB_PATH

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("Recent Pairing Events")
    print("=" * 80)
    
    cursor.execute("""
        SELECT timestamp, invoice_id, delivery_note_id, action, actor_type, model_version
        FROM pairing_events
        ORDER BY timestamp DESC
        LIMIT 20
    """)
    
    events = cursor.fetchall()
    if events:
        print(f"\nFound {len(events)} events:\n")
        print(f"{'Timestamp':<25} {'Action':<15} {'Invoice ID':<20} {'DN ID':<20} {'Actor':<10} {'Model':<15}")
        print("-" * 80)
        for event in events:
            timestamp, inv_id, dn_id, action, actor, model = event
            dn_display = dn_id or "N/A"
            model_display = model or "N/A"
            print(f"{timestamp:<25} {action:<15} {inv_id:<20} {dn_display:<20} {actor:<10} {model_display:<15}")
    else:
        print("\nNo pairing events found.")
    
    # Summary statistics
    cursor.execute("""
        SELECT action, COUNT(*) as count
        FROM pairing_events
        GROUP BY action
        ORDER BY count DESC
    """)
    
    stats = cursor.fetchall()
    if stats:
        print("\n" + "=" * 80)
        print("Event Summary")
        print("=" * 80)
        for action, count in stats:
            print(f"  {action}: {count}")
    
    conn.close()

if __name__ == "__main__":
    main()

