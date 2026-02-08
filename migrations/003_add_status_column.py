"""
Migration: Add status column to invoices
Version: 003
Description: Adds a status column to the invoices table with a default value of 'DRAFT'.
"""

import sqlite3
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import DATABASE_PATH

def upgrade():
    """Apply the migration."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check if migration applied
    cursor.execute("SELECT 1 FROM _migrations WHERE name = ?", ("003_add_status_column",))
    if cursor.fetchone():
        print("Migration 003_add_status_column already applied. Skipping.")
        conn.close()
        return

    # Add status column
    # SQLite doesn't support adding columns with default values easily in older versions, 
    # but for simple text columns it usually works. 
    # If not, we'd need to recreate table, but let's try ALTER TABLE first.
    try:
        cursor.execute("ALTER TABLE invoices ADD COLUMN status TEXT DEFAULT 'DRAFT'")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("Column 'status' already exists. Skipping.")
        else:
            raise e

    # Update existing records to DRAFT
    cursor.execute("UPDATE invoices SET status = 'DRAFT' WHERE status IS NULL")

    # Record migration
    cursor.execute("INSERT INTO _migrations (name) VALUES (?)", ("003_add_status_column",))
    
    conn.commit()
    conn.close()
    print("Migration 003_add_status_column applied successfully.")

def downgrade():
    """Revert the migration."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # SQLite doesn't support DROP COLUMN in older versions. 
    # For now, we'll just leave it or strictly we should recreate table.
    # Given the constraints, let's keep it simple and just remove migration record 
    # (Column remains, but app ignores it if code reverted).
    # Ideally: Create new table without column, copy data, drop old, rename new.
    print("Downgrade for adding column in SQLite is complex. Skipping column drop but reverting migration record.")
    
    cursor.execute("DELETE FROM _migrations WHERE name = ?", ("003_add_status_column",))
    
    conn.commit()
    conn.close()
    print("Migration 003_add_status_column reverted successfully (Metadata only).")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["upgrade", "downgrade"])
    args = parser.parse_args()
    if args.action == "upgrade":
        upgrade()
    elif args.action == "downgrade":
        downgrade()
