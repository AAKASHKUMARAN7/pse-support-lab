"""Make a corrected copy of Ghaf Tree Cafe's file: text dd/mm/yyyy dates -> yyyy-mm-dd.
This mirrors the fix we give the customer (TEXT(DATE(...),"yyyy-mm-dd") helper column)."""
import sys
from datetime import datetime
import openpyxl

src, dst = sys.argv[1], sys.argv[2]
wb = openpyxl.load_workbook(src)
ws = wb["Invoices"]
headers = [c.value for c in ws[1]]
cols = [headers.index(h) + 1 for h in ("Invoice issue date*", "Payment due date*")]
changed = 0
for row in ws.iter_rows(min_row=2):
    for ci in cols:
        cell = row[ci - 1]
        if isinstance(cell.value, str) and "/" in cell.value:
            before = cell.value
            cell.value = datetime.strptime(before, "%d/%m/%Y").strftime("%Y-%m-%d")
            print(f"row {cell.row} {headers[ci-1]}: {before!r} -> {cell.value!r}")
            changed += 1
wb.save(dst)
print(f"{changed} cells changed, saved {dst}")
