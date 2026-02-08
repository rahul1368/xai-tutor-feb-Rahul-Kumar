import pytest
from fastapi.testclient import TestClient
import sqlite3
import os
import sys

# Add parent directory to path to allow importing app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database import get_db, DATABASE_PATH

# Use a separate test database file
TEST_DB_PATH = "test_invoicing.db"

@pytest.fixture(scope="session")
def test_db():
    """Create a temporary test database and apply migrations."""
    # Remove existing test db if any
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    # Create tables manually or via migration script logic
    # For simplicity in tests, we'll execute the CREATE statements directly here
    # mimicking what migrations do.
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    
    # 1. Clients
    cursor.execute("""
        CREATE TABLE clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            company_reg_no TEXT NOT NULL
        )
    """)
    
    # 2. Products
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL
        )
    """)
    
    # 3. Invoices
    cursor.execute("""
        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT NOT NULL UNIQUE,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            client_id INTEGER NOT NULL,
            address TEXT NOT NULL,
            tax REAL DEFAULT 0,
            total REAL DEFAULT 0,
            status TEXT DEFAULT 'DRAFT',
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    """)
    
    # 4. Invoice Items
    cursor.execute("""
        CREATE TABLE invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    """)
    
    # Seed Data
    cursor.execute("INSERT INTO clients (name, address, company_reg_no) VALUES ('Test Client', '123 Test St', 'REG-TEST')")
    cursor.execute("INSERT INTO products (name, price) VALUES ('Test Product', 10.0)")
    
    conn.commit()
    conn.close()
    
    yield TEST_DB_PATH
    
    # Cleanup
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

@pytest.fixture(scope="function")
def client(test_db):
    """
    Override the get_db dependency to use the test database.
    """
    def override_get_db():
        conn = sqlite3.connect(test_db)
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
