"""Basic smoke tests for ClearLedger setup and overview."""
import sqlite3
import unittest
from pathlib import Path
from ledger import storage, reporting


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        storage._create_schema(self.db)
        storage.seed(self.db)

    def tearDown(self):
        self.db.close()

    def test_fresh_demo_baseline(self):
        overview = reporting.get_overview(self.db)
        summary = overview['summary']
        # Business rules: 6 invoices, 5 open invoices, INR 3,209.99 outstanding
        self.assertEqual(summary['invoice_count'], 6)
        self.assertEqual(summary['open_count'], 5)
        self.assertAlmostEqual(summary['outstanding'], 3209.99, places=2)

    def test_customer_count(self):
        customers = storage.get_customers(self.db)
        self.assertEqual(set(customers.keys()), {'HARBOR', 'MAPLE', 'NORTH'})


if __name__ == '__main__':
    unittest.main()
