import sqlite3
import json

# Read health.json to get database path
with open('health.json', 'r') as f:
    h = json.load(f)

db_path = h['db_path_abs']
print(f"Database path: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables in database:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Try to find uploaded files in different possible table names
    possible_tables = ['uploaded_files', 'files', 'uploads', 'documents']
    for table_name in possible_tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"\nTable '{table_name}' has {count} rows")
            
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
                rows = cursor.fetchall()
                print("Sample rows:")
                for row in rows:
                    print(f"  {row}")
        except sqlite3.OperationalError:
            print(f"Table '{table_name}' does not exist")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")