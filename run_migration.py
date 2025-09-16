import sqlite3
import os

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Connect to database
conn = sqlite3.connect("data/owlin.db")

# Read and execute migration
with open("backend/db/migrations/2025_09_16_upload_pipeline.sql", "r") as f:
    migration_sql = f.read()

# Execute migration
conn.executescript(migration_sql)
conn.commit()
conn.close()

print("✅ Migration completed successfully!")
