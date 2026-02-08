"""
Migration: Create invoicing tables
Version: 002
Description: Creates clients, products, invoices, and invoice_items tables and seeds initial data.
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
    
    # Create migrations table if not exists (safety check)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Check if migration applied
    cursor.execute("SELECT 1 FROM _migrations WHERE name = ?", ("002_create_invoicing_tables",))
    if cursor.fetchone():
        print("Migration 002_create_invoicing_tables already applied. Skipping.")
        conn.close()
        return

    # Create Clients Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            company_reg_no TEXT NOT NULL
        )
    """)

    # Create Products Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL
        )
    """)

    # Create Invoices Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT NOT NULL UNIQUE,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            client_id INTEGER NOT NULL,
            address TEXT NOT NULL,
            tax REAL DEFAULT 0,
            total REAL DEFAULT 0,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    """)

    # Create Invoice Items Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    """)

    # Seed Clients
    clients_data = [
        ("Acme Corp", "123 Business Rd, Tech City", "REG-888"),
        ("Globex Inc", "456 Gloomy St, Shadow Valley", "REG-999"),
        ("Soylent Corp", "789 Green Ave, Eco Town", "REG-777")
    ]
    cursor.executemany("INSERT INTO clients (name, address, company_reg_no) VALUES (?, ?, ?)", clients_data)

    # Seed Products
    products_data = [
        ("Widget A", 10.50),
        ("Gadget B", 25.00),
        ("Thingamajig C", 5.99),
        ("Doohickey D", 100.00)
    ]
    cursor.executemany("INSERT INTO products (name, price) VALUES (?, ?)", products_data)

    # Record migration
    cursor.execute("INSERT INTO _migrations (name) VALUES (?)", ("002_create_invoicing_tables",))
    
    conn.commit()
    conn.close()
    print("Migration 002_create_invoicing_tables applied successfully.")

def downgrade():
    """Revert the migration."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS invoice_items")
    cursor.execute("DROP TABLE IF EXISTS invoices")
    cursor.execute("DROP TABLE IF EXISTS products")
    cursor.execute("DROP TABLE IF EXISTS clients")
    
    cursor.execute("DELETE FROM _migrations WHERE name = ?", ("002_create_invoicing_tables",))
    
    conn.commit()
    conn.close()
    print("Migration 002_create_invoicing_tables reverted successfully.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["upgrade", "downgrade"])
    args = parser.parse_args()
    if args.action == "upgrade":
        upgrade()
    elif args.action == "downgrade":
        downgrade()
