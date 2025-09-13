from decimal import Decimal, ROUND_HALF_EVEN, getcontext

getcontext().prec = 28  # high precision for intermediate math

class PackMathError(Exception):
    pass

def d(x) -> Decimal:
    if x is None or x == "":
        return Decimal("0")
    return Decimal(str(x))

def money(x: Decimal) -> Decimal:
    return d(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

def compute_base_units(outer_qty, items_per_outer):
    oq = d(outer_qty)
    ipo = d(items_per_outer) if items_per_outer else Decimal("1")
    if oq < 0 or ipo <= 0:
        raise PackMathError("Invalid pack inputs")
    return oq * ipo

def calc_line_totals(outer_qty, items_per_outer, unit_price, vat_rate_percent):
    base_units = compute_base_units(outer_qty, items_per_outer)
    net = money(d(unit_price) * d(base_units))
    vat = money(net * d(vat_rate_percent) / Decimal("100"))
    gross = money(net + vat)
    return {"base_units": base_units, "net": net, "vat": vat, "gross": gross}
