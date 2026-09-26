"""Regression tests for row-level import validation and error isolation."""
import sqlite3
import unittest
from ledger import storage, importing


class ImportRowValidationRegressionTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        storage._create_schema(self.db)
        for cust_id, cust_name in storage.CUSTOMERS:
            self.db.execute('INSERT INTO customers (id, name) VALUES (?, ?)', (cust_id, cust_name))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_invalid_row_does_not_abort_subsequent_valid_rows(self):
        """
        Input CSV:
        line 1: header
        line 2: valid row 1
        line 3: invalid row (unknown customer)
        line 4: valid row 2
        Expected: imported = 2, rejected = 1, line 3 reported in errors, both valid rows exist in DB.
        """
        csv_content = (
            "customer_id,invoice_number,amount,due_date\n"
            "HARBOR,INV-VALID-1,100.00,2026-11-01\n"
            "UNKNOWN_CUST,INV-INVALID,200.00,2026-11-02\n"
            "MAPLE,INV-VALID-2,300.00,2026-11-03\n"
        )
        res = importing.import_csv(self.db, csv_content, 'invoices')

        self.assertEqual(res['imported'], 2)
        self.assertEqual(res['rejected'], 1)
        self.assertEqual(res['skipped'], 0)
        self.assertEqual(len(res['errors']), 1)
        self.assertEqual(res['errors'][0]['line'], 3)
        self.assertIn("Customer 'UNKNOWN_CUST' does not exist", res['errors'][0]['reason'])

        # Both valid records must exist in database
        rows = self.db.execute('SELECT invoice_number FROM invoices ORDER BY invoice_number').fetchall()
        invoices = [r['invoice_number'] for r in rows]
        self.assertEqual(invoices, ['INV-VALID-1', 'INV-VALID-2'])

    def test_valid_header_with_zero_data_rows(self):
        csv_content = "customer_id,invoice_number,amount,due_date\n"
        res = importing.import_csv(self.db, csv_content, 'invoices')

        self.assertEqual(res['imported'], 0)
        self.assertEqual(res['skipped'], 0)
        self.assertEqual(res['rejected'], 0)
        self.assertEqual(res['errors'], [])

    def test_invalid_header_rejects_whole_import(self):
        csv_content = "wrong,header,cols,here\nHARBOR,INV-1,100.00,2026-11-01\n"
        with self.assertRaises(ValueError):
            importing.import_csv(self.db, csv_content, 'invoices')

        count = self.db.execute('SELECT COUNT(*) FROM invoices').fetchone()[0]
        self.assertEqual(count, 0)

    def test_bom_and_whitespace_support(self):
        # UTF-8 with BOM (\ufeff) and surrounding spaces
        csv_bytes = "\ufeffcustomer_id,invoice_number,amount,due_date\n  HARBOR  ,  INV-BOM  ,  150.50  ,  2026-11-04  \n".encode('utf-8')
        res = importing.import_csv(self.db, csv_bytes, 'invoices')
        self.assertEqual(res['imported'], 1)
        row = self.db.execute('SELECT customer_id, invoice_number, amount FROM invoices WHERE invoice_number = "INV-BOM"').fetchone()
        self.assertEqual(row['customer_id'], 'HARBOR')
        self.assertEqual(row['amount'], 150.50)


if __name__ == '__main__':
    unittest.main()
