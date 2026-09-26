"""Regression tests for invoice re-import identity rules."""
import sqlite3
import unittest
from ledger import storage


class InvoiceReimportRegressionTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        storage._create_schema(self.db)
        for cust_id, cust_name in storage.CUSTOMERS:
            self.db.execute('INSERT INTO customers (id, name) VALUES (?, ?)', (cust_id, cust_name))

        # Initial invoice
        self.initial_inv = {
            'customer_id': 'HARBOR',
            'invoice_number': 'INV-100',
            'amount': 500.00,
            'due_date': '2026-11-15'
        }
        storage.insert_invoice(self.db, self.initial_inv)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_identical_invoice_is_skipped(self):
        # Case A: same customer, invoice_number, amount, due_date
        res = storage.insert_invoice(self.db, dict(self.initial_inv))
        self.assertEqual(res, 'skipped')

        count = self.db.execute('SELECT COUNT(*) FROM invoices').fetchone()[0]
        self.assertEqual(count, 1)

    def test_changed_amount_is_rejected_and_original_preserved(self):
        # Case B1: changed amount
        conflicting = dict(self.initial_inv)
        conflicting['amount'] = 650.00

        with self.assertRaises(ValueError):
            storage.insert_invoice(self.db, conflicting)

        # Verify original record preserved
        row = self.db.execute('SELECT amount, due_date FROM invoices WHERE invoice_number = "INV-100"').fetchone()
        self.assertEqual(row['amount'], 500.00)
        self.assertEqual(row['due_date'], '2026-11-15')

    def test_changed_due_date_is_rejected_and_original_preserved(self):
        # Case B2: changed due date
        conflicting = dict(self.initial_inv)
        conflicting['due_date'] = '2026-12-01'

        with self.assertRaises(ValueError):
            storage.insert_invoice(self.db, conflicting)

        row = self.db.execute('SELECT amount, due_date FROM invoices WHERE invoice_number = "INV-100"').fetchone()
        self.assertEqual(row['amount'], 500.00)
        self.assertEqual(row['due_date'], '2026-11-15')

    def test_new_invoice_identity_is_imported(self):
        # Case C: New invoice
        new_inv = {
            'customer_id': 'MAPLE',
            'invoice_number': 'INV-200',
            'amount': 750.00,
            'due_date': '2026-11-20'
        }
        res = storage.insert_invoice(self.db, new_inv)
        self.assertEqual(res, 'imported')

        count = self.db.execute('SELECT COUNT(*) FROM invoices').fetchone()[0]
        self.assertEqual(count, 2)


if __name__ == '__main__':
    unittest.main()
