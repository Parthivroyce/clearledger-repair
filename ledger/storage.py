"""Database connection, schema setup, seeding, and record persistence."""
import sqlite3
from pathlib import Path
from ledger import matching

CUSTOMERS = [
    ('HARBOR', 'Harbor Logistics'),
    ('MAPLE', 'Maple & Co'),
    ('NORTH', 'North Services')
]

DEMO_INVOICES = [
    ('HARBOR', 'INV-101', 1000.00, '2026-10-15'),
    ('HARBOR', 'INV-102', 1209.99, '2026-10-20'),
    ('MAPLE', 'INV-201', 500.00, '2026-10-10'),
    ('MAPLE', 'INV-202', 300.00, '2026-10-25'),
    ('NORTH', 'INV-301', 450.00, '2026-10-05'),
    ('NORTH', 'INV-302', 500.00, '2026-10-30')
]

DEMO_PAYMENTS = [
    ('PAY-1', 'HARBOR', 'INV-101', 250.00),
    ('PAY-2', 'MAPLE', 'INV-201', 500.00)
]


def connect(db_path):
    """Connect to SQLite database and ensure tables exist."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON;')
    _create_schema(db)
    return db


def _create_schema(db):
    """Initialize schema tables."""
    db.executescript('''
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL REFERENCES customers(id),
            invoice_number TEXT NOT NULL,
            amount REAL NOT NULL,
            due_date TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS payments (
            payment_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL REFERENCES customers(id),
            invoice_number TEXT NOT NULL,
            amount REAL NOT NULL,
            invoice_id INTEGER REFERENCES invoices(id)
        );
    ''')
    db.commit()


def seed(db):
    """Seed customers and fresh demo records if database is empty."""
    for cust_id, cust_name in CUSTOMERS:
        db.execute(
            'INSERT OR IGNORE INTO customers (id, name) VALUES (?, ?)',
            (cust_id, cust_name)
        )
    db.commit()

    count = db.execute('SELECT COUNT(*) FROM invoices').fetchone()[0]
    if count == 0:
        for cust_id, inv_num, amt, due in DEMO_INVOICES:
            db.execute(
                'INSERT INTO invoices (customer_id, invoice_number, amount, due_date) VALUES (?, ?, ?, ?)',
                (cust_id, inv_num, amt, due)
            )
        for pay_id, cust_id, inv_num, amt in DEMO_PAYMENTS:
            inv_id = matching.find_invoice_for_payment(db, {'customer_id': cust_id, 'invoice_number': inv_num})
            db.execute(
                'INSERT INTO payments (payment_id, customer_id, invoice_number, amount, invoice_id) VALUES (?, ?, ?, ?, ?)',
                (pay_id, cust_id, inv_num, amt, inv_id)
            )
        db.commit()


def get_customers(db):
    """Return dictionary of customer_id -> customer_name."""
    rows = db.execute('SELECT id, name FROM customers').fetchall()
    return {row['id']: row['name'] for row in rows}


def insert_invoice(db, invoice):
    """
    Insert an invoice enforcing identity rules (customer_id, invoice_number).
    Returns 'imported' or 'skipped', or raises ValueError (rejected).
    """
    existing = db.execute(
        'SELECT * FROM invoices WHERE customer_id = ? AND invoice_number = ?',
        (invoice['customer_id'], invoice['invoice_number'])
    ).fetchone()

    if existing is not None:
        # Case A: Same identity + same amount + same due date -> skipped
        if (round(float(existing['amount']), 2) == round(float(invoice['amount']), 2) and
                str(existing['due_date']) == str(invoice['due_date'])):
            return 'skipped'
        # Case B: Same identity with different details -> rejected
        raise ValueError(
            f"Invoice {invoice['invoice_number']} for customer {invoice['customer_id']} "
            f"already exists with different details (existing: amount={existing['amount']}, due={existing['due_date']}; "
            f"incoming: amount={invoice['amount']}, due={invoice['due_date']})"
        )

    # Case C: New invoice identity -> imported
    db.execute(
        'INSERT INTO invoices (customer_id, invoice_number, amount, due_date) VALUES (?, ?, ?, ?)',
        (invoice['customer_id'], invoice['invoice_number'], invoice['amount'], invoice['due_date'])
    )
    return 'imported'


def insert_payment(db, payment):
    """
    Insert a payment enforcing payment_id identity.
    Returns 'imported' or 'skipped', or raises ValueError (rejected).
    """
    existing = db.execute(
        'SELECT * FROM payments WHERE payment_id = ?',
        (payment['payment_id'],)
    ).fetchone()

    if existing is not None:
        # Check if identical details
        if (existing['customer_id'] == payment['customer_id'] and
                existing['invoice_number'] == payment['invoice_number'] and
                round(float(existing['amount']), 2) == round(float(payment['amount']), 2)):
            return 'skipped'
        raise ValueError(
            f"Payment {payment['payment_id']} already exists with different details"
        )

    invoice_id = matching.find_invoice_for_payment(db, payment)
    db.execute(
        'INSERT INTO payments (payment_id, customer_id, invoice_number, amount, invoice_id) VALUES (?, ?, ?, ?, ?)',
        (payment['payment_id'], payment['customer_id'], payment['invoice_number'], payment['amount'], invoice_id)
    )
    return 'imported'
