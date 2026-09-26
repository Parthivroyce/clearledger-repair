"""CSV importing logic for invoices and payments."""
import csv
import io
from ledger import storage, validation


def import_csv(db, raw_content, kind):
    """
    Import raw CSV content (bytes or str) for 'invoices' or 'payments'.
    Returns dict:
      {"imported": int, "skipped": int, "rejected": int, "errors": list}
    Raises ValueError on invalid header or kind (leading to HTTP 400).
    """
    if kind not in ('invoices', 'payments'):
        raise ValueError(f"Invalid import kind: '{kind}'. Must be 'invoices' or 'payments'.")

    if isinstance(raw_content, bytes):
        text = raw_content.decode('utf-8-sig')
    else:
        # Strip potential BOM character from string
        text = raw_content.lstrip('\ufeff')

    reader = csv.reader(io.StringIO(text))

    try:
        header = next(reader)
    except StopIteration:
        raise ValueError("CSV file is empty; expected header row")

    validation.validate_header(header, kind)

    imported = 0
    skipped = 0
    rejected = 0
    errors = []

    valid_customers = set(storage.get_customers(db).keys())

    # Line numbering: header is line 1, first data row is line 2
    for line_number, row in enumerate(reader, start=2):
        if not row or all(not col.strip() for col in row):
            # Skip empty lines without rejecting or count
            continue

        try:
            # Per-row normalization & validation
            normalized = validation.normalize_row(row, kind, valid_customers)
            if kind == 'invoices':
                res = storage.insert_invoice(db, normalized)
            else:
                res = storage.insert_payment(db, normalized)

            if res == 'imported':
                imported += 1
            elif res == 'skipped':
                skipped += 1
        except Exception as e:
            rejected += 1
            errors.append({
                'line': line_number,
                'reason': str(e)
            })

    db.commit()

    return {
        'imported': imported,
        'skipped': skipped,
        'rejected': rejected,
        'errors': errors
    }
