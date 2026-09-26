"""Regression tests for invoice reporting and status filtering."""
import sqlite3
import unittest
from ledger import storage, reporting


class ReportingRegressionTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        storage._create_schema(self.db)
        for cust_id, cust_name in storage.CUSTOMERS:
            self.db.execute('INSERT INTO customers (id, name) VALUES (?, ?)', (cust_id, cust_name))

        # Seed three distinct invoice scenarios:
        # 1. Unpaid / positive balance (Open)
        storage.insert_invoice(self.db, {
            'customer_id': 'HARBOR',
            'invoice_number': 'INV-OPEN',
            'amount': 300.00,
            'due_date': '2026-11-10'
        })
        # 2. Exactly paid / zero balance (Paid)
        storage.insert_invoice(self.db, {
            'customer_id': 'MAPLE',
            'invoice_number': 'INV-PAID',
            'amount': 200.00,
            'due_date': '2026-11-11'
        })
        storage.insert_payment(self.db, {
            'payment_id': 'PAY-PAID',
            'customer_id': 'MAPLE',
            'invoice_number': 'INV-PAID',
            'amount': 200.00
        })
        # 3. Overpaid / negative balance (Paid)
        storage.insert_invoice(self.db, {
            'customer_id': 'NORTH',
            'invoice_number': 'INV-OVERPAID',
            'amount': 150.00,
            'due_date': '2026-11-12'
        })
        storage.insert_payment(self.db, {
            'payment_id': 'PAY-OVERPAID',
            'customer_id': 'NORTH',
            'invoice_number': 'INV-OVERPAID',
            'amount': 200.00
        })
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_open_filter_returns_only_positive_balance(self):
        open_invoices = reporting.get_invoices(self.db, status='open')
        self.assertEqual(len(open_invoices), 1)
        self.assertEqual(open_invoices[0]['invoice_number'], 'INV-OPEN')
        self.assertGreater(open_invoices[0]['balance'], 0)
        self.assertEqual(open_invoices[0]['status'], 'open')

    def test_paid_filter_returns_zero_and_negative_balances(self):
        paid_invoices = reporting.get_invoices(self.db, status='paid')
        self.assertEqual(len(paid_invoices), 2)
        paid_numbers = {inv['invoice_number'] for inv in paid_invoices}
        self.assertEqual(paid_numbers, {'INV-PAID', 'INV-OVERPAID'})
        for inv in paid_invoices:
            self.assertLessEqual(inv['balance'], 0)
            self.assertEqual(inv['status'], 'paid')

    def test_all_filter_returns_all(self):
        all_invoices = reporting.get_invoices(self.db, status='all')
        self.assertEqual(len(all_invoices), 3)

    def test_invalid_status_raises_value_error(self):
        with self.assertRaises(ValueError):
            reporting.get_invoices(self.db, status='pending')
        with self.assertRaises(ValueError):
            reporting.get_invoices(self.db, status='')


if __name__ == '__main__':
    unittest.main()
