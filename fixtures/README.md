# Existing register fixture

This fixture represents the business owner's active working register, which must be preserved during and after all application repairs.

## Register contents

- 3 customers: `HARBOR`, `MAPLE`, `NORTH`
- 9 invoices (`KEEP-700` through `KEEP-708`)
- 5 payments (`KEEP-P1`, `KEEP-P2`, `KEEP-P3`, `KEEP-P4`, `KEEP-U1`)
- 7 open invoices
- 2 paid invoices
- INR 3,698.19 total outstanding
- 1 unmatched payment (`KEEP-U1`)

## Restoration

To restore this fixture into the active database:

```text
python restore_fixture.py --replace
```
