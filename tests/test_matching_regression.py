"""Regression tests for payment-to-invoice matching."""
import sqlite3
import unittest
from ledger import storage, matching, importing


class MatchingRegressionTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        storage._create_schema(self.db)
        # Seed customers without demo invoices
        for cust_id, cust_name in storage.CUSTOMERS:
            self.db.execute('INSERT INTO customers (id, name) VALUES (?, ?)', (cust_id, cust_name))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_amount_alone_does_not_match_payment(self):
        """
        Two invoices with identical amounts (500.00) for different identities:
          Inv A: (HARBOR, INV-A)
          Inv B: (MAPLE, INV-B)
        A payment referencing (HARBOR, INV-A) for 500.00 must attach ONLY to Inv A.
        A payment referencing (NORTH, INV-C) for 500.00 must NOT attach to either Inv A or Inv B.
        """
        storage.insert_invoice(self.db, {
            'customer_id': 'HARBOR',
            'invoice_number': 'INV-A',
            'amount': 500.00,
            'due_date': '2026-11-01'
        })
        storage.insert_invoice(self.db, {
            'customer_id': 'MAPLE',
            'invoice_number': 'INV-B',
            'amount': 500.00,
            'due_date': '2026-11-02'
        })
        self.db.commit()

        # Payment for Inv A
        storage.insert_payment(self.db, {
            'payment_id': 'PAY-A',
            'customer_id': 'HARBOR',
            'invoice_number': 'INV-A',
            'amount': 500.00
        })
        # Payment for non-existent Inv C with identical amount
        storage.insert_payment(self.db, {
            'payment_id': 'PAY-C',
            'customer_id': 'NORTH',
            'invoice_number': 'INV-C',
            'amount': 500.00
        })
        self.db.commit()

        inv_a = self.db.execute('SELECT id FROM invoices WHERE invoice_number = "INV-A"').fetchone()
        inv_b = self.db.execute('SELECT id FROM invoices WHERE invoice_number = "INV-B"').fetchone()

        pay_a = self.db.execute('SELECT invoice_id FROM payments WHERE payment_id = "PAY-A"').fetchone()
        pay_c = self.db.execute('SELECT invoice_id FROM payments WHERE payment_id = "PAY-C"').fetchone()

        self.assertEqual(pay_a['invoice_id'], inv_a['id'])
        self.assertIsNone(pay_c['invoice_id'], "Payment PAY-C must remain unmatched even though amount matches existing invoices")

    def test_unmatched_payment_does_not_rematch_later(self):
        """
        Valid payment with no matching invoice remains unmatched (invoice_id is NULL).
        It must not automatically rematch when a matching invoice is subsequently imported.
        """
        # Insert payment first
        storage.insert_payment(self.db, {
            'payment_id': 'PAY-EARLY',
            'customer_id': 'HARBOR',
            'invoice_number': 'INV-LATER',
            'amount': 250.00
        })
        self.db.commit()

        early_pay = self.db.execute('SELECT invoice_id FROM payments WHERE payment_id = "PAY-EARLY"').fetchone()
        self.assertIsNone(early_pay['invoice_id'])

        # Now import the matching invoice
        storage.insert_invoice(self.db, {
            'customer_id': 'HARBOR',
            'invoice_number': 'INV-LATER',
            'amount': 250.00,
            'due_date': '2026-12-01'
        })
        self.db.commit()

        # The existing payment must STILL be unmatched
        pay_after = self.db.execute('SELECT invoice_id FROM payments WHERE payment_id = "PAY-EARLY"').fetchone()
        self.assertIsNone(pay_after['invoice_id'], "Unmatched payment must not automatically rematch after future invoice import")


if __name__ == '__main__':
    unittest.main()
