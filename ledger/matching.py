"""Payment to invoice matching logic."""


def find_invoice_for_payment(db, payment):
    """
    Finds matching invoice for payment.
    Matching strictly requires:
      payment.customer_id == invoice.customer_id AND
      payment.invoice_number == invoice.invoice_number
    Amount alone must NEVER establish identity.
    Returns invoice ID if matched, or None.
    """
    row = db.execute(
        'SELECT id FROM invoices WHERE customer_id = ? AND invoice_number = ?',
        (payment['customer_id'], payment['invoice_number'])
    ).fetchone()
    if row is not None:
        return row['id']
    return None
