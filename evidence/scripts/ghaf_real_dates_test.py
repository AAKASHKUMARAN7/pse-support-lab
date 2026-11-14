"""Test file: Ghaf's rows with the text dates turned into REAL Excel date cells (what
Data > Text to Columns > Date: DMY produces), invoice numbers prefixed TEST- so they
don't clash with the real GTC invoices already accepted."""
import sys
from datetime import datetime
import openpyxl
src, dst = sys.argv[1], sys.argv[2]
wb = openpyxl.load_workbook(src); ws = wb["Invoices"]
h = [c.value for c in ws[1]]
for row in ws.iter_rows(min_row=2):
    for name in ("Invoice issue date*", "Payment due date*"):
        c = row[h.index(name)]
        c.value = datetime.strptime(c.value, "%d/%m/%Y"); c.number_format = "dd/mm/yyyy"
    n = row[h.index("Invoice number*")]; n.value = "TEST-" + n.value
wb.save(dst); print("saved", dst)
