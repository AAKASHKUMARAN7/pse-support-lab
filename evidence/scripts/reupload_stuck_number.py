"""Build a test file for Desert Rose (seller 1) whose first invoice re-uses an invoice number
that is stuck in status Parsed (inside an import killed by the OOM)."""
import sys, openpyxl
src, dst, number = sys.argv[1], sys.argv[2], sys.argv[3]
wb = openpyxl.load_workbook(src); ws = wb["Invoices"]
h = [c.value for c in ws[1]]; col = h.index("Invoice number*")
keep = None
for r in range(ws.max_row, 1, -1):
    v = ws.cell(r, col + 1).value
    if keep is None: keep = "DRT-2611-001"
    if v == keep: ws.cell(r, col + 1).value = number
    else: ws.delete_rows(r)
wb.save(dst); print("saved", dst, "with invoice number", number)
