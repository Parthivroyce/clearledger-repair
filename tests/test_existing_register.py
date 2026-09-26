"""Tests for preserving the owner's existing register and ongoing workflows."""
import json
import sqlite3
import unittest
from pathlib import Path
from ledger import storage, reporting, importing

ROOT = Path(__file__).resolve().parent.parent


class ExistingRegisterTests(unittest.TestCase):
    def setUp(self):
        fixture_path = ROOT / 'fixtures' / 'existing-register.sqlite3'
        self.assertTrue(fixture_path.exists(), "Existing register fixture must exist")

        # Copy fixture to in-memory database to preserve the original fixture file untouched
        source_db = sqlite3.connect(fixture_path)
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        source_db.backup(self.db)
        source_db.close()

    def tearDown(self):
        self.db.close()

    def test_existing_register_records_and_totals(self):
        """
        Verify the owner's existing register baseline:
        - 3 customers
        - 9 invoices
        - 5 payments
        - 7 open invoices
        - 2 paid invoices
        - INR 3,698.19 outstanding
        - 1 unmatched payment
        """
        overview = reporting.get_overview(self.db)
        summary = overview['summary']

        self.assertEqual(summary['invoice_count'], 9)
        self.assertEqual(summary['open_count'], 7)
        self.assertAlmostEqual(summary['outstanding'], 3698.19, places=2)
        self.assertEqual(len(overview['unmatched_payments']), 1)

        unmatched = overview['unmatched_payments'][0]
        self.assertEqual(unmatched['payment_id'], 'KEEP-U1')
        self.assertEqual(unmatched['customer_id'], 'HARBOR')

        # Check total payments in db
        total_payments = self.db.execute('SELECT COUNT(*) FROM payments').fetchone()[0]
        self.assertEqual(total_payments, 5)

        # Check total customers
        total_customers = self.db.execute('SELECT COUNT(*) FROM customers').fetchone()[0]
        self.assertEqual(total_customers, 3)

    def test_subsequent_valid_imports_on_existing_register(self):
        """
        After loading the existing register, valid new invoice and payment imports must work
        without corrupting existing records.
        """
        # Import new invoice
        new_invoice_csv = "customer_id,invoice_number,amount,due_date\nNORTH,NEW-INV-1,450.00,2026-12-01\n"
        inv_res = importing.import_csv(self.db, new_invoice_csv, 'invoices')
        self.assertEqual(inv_res['imported'], 1)

        # Import payment matching the new invoice
        new_payment_csv = "payment_id,customer_id,invoice_number,amount\nNEW-PAY-1,NORTH,NEW-INV-1,450.00\n"
        pay_res = importing.import_csv(self.db, new_payment_csv, 'payments')
        self.assertEqual(pay_res['imported'], 1)

        # Outstanding should remain 3,698.19 because the new invoice was fully paid
        overview = reporting.get_overview(self.db)
        self.assertAlmostEqual(overview['summary']['outstanding'], 3698.19, places=2)
        self.assertEqual(overview['summary']['invoice_count'], 10)


if __name__ == '__main__':
    unittest.main()
