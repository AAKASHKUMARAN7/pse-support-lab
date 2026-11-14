"""Inspect sample workbooks: cell types of date columns and Al Noor line maths."""
import sys
from decimal import Decimal, ROUND_HALF_UP
from collections import OrderedDict
import openpyxl

def rows(path):
    wb = openpyxl.load_workbook(path)
    ws = wb["Invoices"]
    it = ws.iter_rows()
    headers = [c.value for c in next(it)]
    for r in it:
        if all(c.value is None for c in r):
            continue
        yield r[0].row, {h: c for h, c in zip(headers, r)}

print("=== Ghaf Tree Cafe: date cells ===")
for n, r in rows("samples/ghaf-cafe-nov-2026.xlsx"):
    for col in ("Invoice issue date*", "Payment due date*"):
        c = r[col]
        print(f"row {n} {r['Invoice number*'].value:<14} {col:<22} value={c.value!r:<14} python_type={type(c.value).__name__:<9} cell_type={c.data_type} format={c.number_format}")

print()
print("=== Al Noor Fuel: per-invoice totals, portal method vs correct method ===")
q2 = Decimal("0.01")
r2 = lambda d: d.quantize(q2, rounding=ROUND_HALF_UP)
invs = OrderedDict()
for n, r in rows("samples/al-noor-fuel-nov-2026.xlsx"):
    invs.setdefault(r["Invoice number*"].value, []).append((n, r))
for num, lines in invs.items():
    net = vat = gross_portal = Decimal(0)
    for n, r in lines:
        qty = Decimal(str(r["Itemquantity*"].value)); price = Decimal(str(r["Item net price*"].value))
        line_net = Decimal(str(r["Invoice line net amount*"].value)); rate = Decimal(str(r["Invoiced item VAT rate*"].value))
        line_vat = r2(line_net * rate / 100)
        net += line_net; vat += line_vat
        gross_portal += qty * price * (1 + rate / 100)
        print(f"  {num} row {n}: qty={qty} price={price} qty*price={qty*price} line_net={line_net} diff={line_net - qty*price:+} vat={line_vat}")
    print(f"{num}: excl={r2(net)} vat={r2(vat)} excl+vat={r2(net)+r2(vat)} | portal TaxInclusive=round2(sum qty*price*1.05)={r2(gross_portal)} -> {'OK' if r2(net)+r2(vat)==r2(gross_portal) else 'BR-CO-15 MISMATCH'}")
