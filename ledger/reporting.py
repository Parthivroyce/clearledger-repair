"""Reporting and export utilities for invoices and overview."""
import csv
import io


def get_invoices(db, status='all'):
    """
    Retrieve invoices filtered by status:
    - 'all': all invoices
    - 'open': invoices with balance > 0
    - 'paid': invoices with balance <= 0
    Raises ValueError for any other status.
    """
    if status not in ('all', 'open', 'paid'):
        raise ValueError(f"Invalid status: '{status}'. Must be 'all', 'open', or 'paid'.")

    rows = db.execute('''
        SELECT
            i.id,
            i.customer_id,
            c.name AS customer_name,
            i.invoice_number,
            i.amount,
            i.due_date,
            COALESCE(SUM(p.amount), 0.0) AS paid
        FROM invoices i
        JOIN customers c ON i.customer_id = c.id
        LEFT JOIN payments p ON p.invoice_id = i.id
        GROUP BY i.id
        ORDER BY i.id
    ''').fetchall()

    results = []
    for r in rows:
        amount = round(float(r['amount']), 2)
        paid = round(float(r['paid']), 2)
        balance = round(amount - paid, 2)
        computed_status = 'open' if balance > 0 else 'paid'

        if status == 'open' and computed_status != 'open':
            continue
        if status == 'paid' and computed_status != 'paid':
            continue

        results.append({
            'id': r['id'],
            'customer_id': r['customer_id'],
            'customer_name': r['customer_name'],
            'invoice_number': r['invoice_number'],
            'amount': amount,
            'due_date': r['due_date'],
            'paid': paid,
            'balance': balance,
            'status': computed_status
        })
    return results


def get_overview(db):
    """
    Returns overview object containing summary, all invoices, and unmatched payments.
    """
    all_invoices = get_invoices(db, 'all')
    open_invoices = [inv for inv in all_invoices if inv['status'] == 'open']
    outstanding = round(sum(inv['balance'] for inv in open_invoices if inv['balance'] > 0), 2)

    unmatched_rows = db.execute('''
        SELECT payment_id, customer_id, invoice_number, amount
        FROM payments
        WHERE invoice_id IS NULL
        ORDER BY payment_id
    ''').fetchall()

    unmatched_payments = [
        {
            'payment_id': r['payment_id'],
            'customer_id': r['customer_id'],
            'invoice_number': r['invoice_number'],
            'amount': round(float(r['amount']), 2)
        }
        for r in unmatched_rows
    ]

    return {
        'summary': {
            'invoice_count': len(all_invoices),
            'open_count': len(open_invoices),
            'outstanding': outstanding
        },
        'invoices': all_invoices,
        'unmatched_payments': unmatched_payments
    }


def get_export_csv(db):
    """
    Generate CSV export of all invoices formatted to 2 decimal places.
    """
    invoices = get_invoices(db, 'all')
    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(['customer_id', 'invoice_number', 'amount', 'paid', 'balance', 'status'])
    for inv in invoices:
        writer.writerow([
            inv['customer_id'],
            inv['invoice_number'],
            f"{inv['amount']:.2f}",
            f"{inv['paid']:.2f}",
            f"{inv['balance']:.2f}",
            inv['status']
        ])
    return output.getvalue()
