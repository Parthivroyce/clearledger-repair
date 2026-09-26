"""Tests for the small useful improvement: actionable import error diagnostics."""
import sqlite3
import unittest
from ledger import storage, importing


class ImprovementActionableErrorsTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        storage._create_schema(self.db)
        for cust_id, cust_name in storage.CUSTOMERS:
            self.db.execute('INSERT INTO customers (id, name) VALUES (?, ?)', (cust_id, cust_name))
        storage.insert_invoice(self.db, {
            'customer_id': 'HARBOR',
            'invoice_number': 'INV-100',
            'amount': 500.00,
            'due_date': '2026-11-15'
        })
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_customer_error_provides_available_customers(self):
        csv_content = "customer_id,invoice_number,amount,due_date\nACME,INV-200,100.00,2026-11-20\n"
        res = importing.import_csv(self.db, csv_content, 'invoices')
        self.assertEqual(res['rejected'], 1)
        reason = res['errors'][0]['reason']
        self.assertIn("Available customers", reason)
        self.assertIn("HARBOR", reason)
        self.assertIn("MAPLE", reason)
        self.assertIn("NORTH", reason)

    def test_conflict_error_explains_exact_mismatch(self):
        # Incoming invoice with conflicting amount
        csv_content = "customer_id,invoice_number,amount,due_date\nHARBOR,INV-100,999.00,2026-11-15\n"
        res = importing.import_csv(self.db, csv_content, 'invoices')
        self.assertEqual(res['rejected'], 1)
        reason = res['errors'][0]['reason']
        self.assertIn("already exists with different details", reason)
        self.assertIn("existing", reason)
        self.assertIn("incoming", reason)


if __name__ == '__main__':
    unittest.main()
