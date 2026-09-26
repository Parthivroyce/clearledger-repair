"""Input validation and normalization for ClearLedger."""
from datetime import datetime
import re

INVOICE_HEADER = ['customer_id', 'invoice_number', 'amount', 'due_date']
PAYMENT_HEADER = ['payment_id', 'customer_id', 'invoice_number', 'amount']
AMOUNT_REGEX = re.compile(r'^\d+(\.\d{1,2})?$')


def validate_header(header, kind):
    """Validate CSV header line. Raises ValueError on mismatch."""
    expected = INVOICE_HEADER if kind == 'invoices' else PAYMENT_HEADER
    cleaned_header = [col.strip() for col in header]
    if cleaned_header != expected:
        raise ValueError(f"Invalid CSV header for {kind}. Expected: {','.join(expected)}")


def validate_amount(raw_val):
    """Validate that amount is a positive decimal <= 10,000,000 with at most 2 decimal places."""
    val_str = raw_val.strip()
    if not val_str:
        raise ValueError("Amount is required and cannot be empty")
    if not AMOUNT_REGEX.match(val_str):
        raise ValueError(f"Amount '{val_str}' must be a positive decimal with at most two decimal places")
    amount = float(val_str)
    if amount <= 0:
        raise ValueError(f"Amount {amount} must be greater than zero")
    if amount > 10_000_000:
        raise ValueError(f"Amount {amount} cannot exceed 10,000,000")
    return round(amount, 2)


def validate_date(raw_val):
    """Validate that date is YYYY-MM-DD format."""
    val_str = raw_val.strip()
    if not val_str:
        raise ValueError("Date is required and cannot be empty")
    try:
        parsed = datetime.strptime(val_str, '%Y-%m-%d')
        # Ensure exact YYYY-MM-DD format without extra components
        if parsed.strftime('%Y-%m-%d') != val_str:
            raise ValueError()
        return val_str
    except Exception:
        raise ValueError(f"Date '{val_str}' must be a valid date in YYYY-MM-DD format")


def normalize_row(row, kind, valid_customers):
    """
    Validates and normalizes a single data row.
    Returns a dict with clean fields or raises ValueError.
    """
    expected_header = INVOICE_HEADER if kind == 'invoices' else PAYMENT_HEADER
    if len(row) != len(expected_header):
        raise ValueError(f"Row has {len(row)} columns, expected {len(expected_header)}")

    trimmed = [col.strip() for col in row]
    data = dict(zip(expected_header, trimmed))

    # Check for empty fields
    for field, val in data.items():
        if not val:
            raise ValueError(f"Field '{field}' cannot be empty")

    # Customer check
    customer_id = data['customer_id']
    if customer_id not in valid_customers:
        valid_list = ', '.join(sorted(valid_customers))
        raise ValueError(f"Customer '{customer_id}' does not exist. Available customers: {valid_list}")

    # Amount check
    data['amount'] = validate_amount(data['amount'])

    if kind == 'invoices':
        data['due_date'] = validate_date(data['due_date'])

    return data
