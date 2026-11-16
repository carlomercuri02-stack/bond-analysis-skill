#!/usr/bin/env python3
"""
bond_calc.py - deterministic fixed-rate bond calculator (stdlib only).

Given a bond's terms plus EITHER a clean price OR a yield, prints one JSON
object with: clean/dirty price, accrued interest, yield to maturity,
current yield, Macaulay/modified duration, convexity, DV01 and optional
interest-rate scenarios.

Conventions (street convention, same as Bloomberg YAS / Excel PRICE for
30/360 bonds):
  - Cash flows on a regular coupon schedule counted back from maturity.
  - Day count 30/360 (US) by default; "act/act" available.
  - Fractional first period: w = days(settlement -> next coupon) / days(period).
  - dirty = sum CF_k / (1 + y/f)^(w + k),  k = 0..n-1
  - Accrued = coupon_per_period * (1 - w).
  - Yield is an annual nominal yield compounded f times a year.

Usage examples:
  python bond_calc.py --coupon 4.8 --maturity 2027-02-26 --settlement 2026-11-12 --price 100.00
  python bond_calc.py --coupon 5 --maturity 2036-01-15 --settlement 2026-01-15 --yield 6 --shocks -100,-50,50,100
"""
import argparse
import calendar
import json
import sys
from datetime import date, datetime, timedelta


# ----------------------------- dates ---------------------------------------
def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def add_months(d, months, anchor_day):
    """d shifted by `months`, using anchor_day clamped to month length
    (so a 31st-maturity bond pays on month-ends, no drift)."""
    idx = d.year * 12 + (d.month - 1) + months
    y, m = divmod(idx, 12)
    m += 1
    return date(y, m, min(anchor_day, calendar.monthrange(y, m)[1]))


def add_business_days(d, n):
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def days_30_360(d1, d2):
    """US (bond basis) 30/360."""
    day1, day2 = min(d1.day, 30), d2.day
    if day1 == 30 and day2 == 31:
        day2 = 30
    return (d2.year - d1.year) * 360 + (d2.month - d1.month) * 30 + (day2 - day1)


def day_diff(d1, d2, basis):
    return days_30_360(d1, d2) if basis == "30/360" else (d2 - d1).days


def coupon_dates(maturity, freq):
    """All coupon dates, ascending, counted back from maturity far enough to
    cover any settlement; caller slices what it needs."""
    step = 12 // freq
    dates, k = [], 0
    while k < 400:
        dates.append(add_months(maturity, -step * k, maturity.day))
        k += 1
    return sorted(dates)


# ----------------------------- core maths ----------------------------------
def build_cashflows(coupon_pct, maturity, settlement, freq, redemption, basis):
    """Returns (list of (t_periods, cash_flow), accrued, w).
    t_periods = w + k, i.e. periods from settlement to each payment."""
    if settlement >= maturity:
        raise ValueError("settlement must be before maturity")
    dates = coupon_dates(maturity, freq)
    prev = max(d for d in dates if d <= settlement)
    nxt = min(d for d in dates if d > settlement)
    period_days = day_diff(prev, nxt, basis)
    w = day_diff(settlement, nxt, basis) / period_days
    c = coupon_pct / freq  # coupon per period, per 100 face
    remaining = [d for d in dates if d >= nxt and d <= maturity]
    flows = []
    for k, _ in enumerate(remaining):
        cf = c + (redemption if k == len(remaining) - 1 else 0.0)
        flows.append((w + k, cf))
    accrued = c * (1 - w)
    return flows, accrued, w


def dirty_from_yield(flows, y_pct, freq):
    r = y_pct / 100 / freq
    return sum(cf / (1 + r) ** t for t, cf in flows)


def yield_from_dirty(flows, dirty, freq):
    lo, hi = -0.99 * freq * 100, 1000.0  # in %, bracket wide
    f = lambda y: dirty_from_yield(flows, y, freq) - dirty
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        raise ValueError("could not bracket a yield for this price (check inputs)")
    for _ in range(300):
        mid = (lo + hi) / 2
        fm = f(mid)
        if abs(fm) < 1e-12:
            break
        if flo * fm < 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


def risk_measures(flows, y_pct, freq):
    r = y_pct / 100 / freq
    pv = [(t, cf / (1 + r) ** t) for t, cf in flows]
    dirty = sum(p for _, p in pv)
    mac = sum((t / freq) * p for t, p in pv) / dirty            # years
    mod = mac / (1 + r)                                          # years
    conv = sum(p * t * (t + 1) for t, p in pv) / (dirty * (1 + r) ** 2 * freq ** 2)
    return {"macaulay_duration_years": mac, "modified_duration_years": mod,
            "convexity": conv, "dv01_per_100_face": mod * dirty / 10000}


def r6(x):
    return None if x is None else round(x, 6)


# ----------------------------- main ----------------------------------------
def analyse(a):
    maturity = parse_date(a.maturity)
    settlement = parse_date(a.settlement) if a.settlement else add_business_days(date.today(), 2)
    flows, accrued, w = build_cashflows(a.coupon, maturity, settlement, a.freq, a.redemption, a.basis)

    if (a.price is None) == (a.yield_pct is None):
        raise ValueError("provide exactly one of --price (clean) or --yield")
    if a.price is not None:
        dirty = a.price + accrued
        ytm = yield_from_dirty(flows, dirty, a.freq)
        clean = a.price
        mode = "price_to_yield"
    else:
        ytm = a.yield_pct
        dirty = dirty_from_yield(flows, ytm, a.freq)
        clean = dirty - accrued
        mode = "yield_to_price"

    rm = risk_measures(flows, ytm, a.freq)
    out = {
        "inputs": {"coupon_pct": a.coupon, "maturity": maturity.isoformat(),
                   "settlement": settlement.isoformat(), "frequency": a.freq,
                   "redemption": a.redemption, "day_count": a.basis,
                   "mode": mode},
        "cash_flows_remaining": len(flows),
        "years_to_maturity": r6((maturity - settlement).days / 365.25),
        "clean_price": r6(clean), "accrued_interest": r6(accrued),
        "dirty_price": r6(dirty), "ytm_pct": r6(ytm),
        "current_yield_pct": r6(a.coupon / clean * 100),
        **{k: r6(v) for k, v in rm.items()},
    }
    if a.shocks:
        sc = []
        for bp in a.shocks:
            y2 = ytm + bp / 100
            d2 = dirty_from_yield(flows, y2, a.freq)
            exact = d2 / dirty - 1
            dur_only = -rm["modified_duration_years"] * bp / 10000
            dur_conv = dur_only + 0.5 * rm["convexity"] * (bp / 10000) ** 2
            sc.append({"shock_bps": bp, "new_ytm_pct": r6(y2),
                       "new_clean_price": r6(d2 - accrued),
                       "price_change_pct_exact": r6(exact * 100),
                       "price_change_pct_duration_only": r6(dur_only * 100),
                       "price_change_pct_duration_plus_convexity": r6(dur_conv * 100)})
        out["scenarios"] = sc
    out["notes"] = ["Accrued and settlement dates follow the convention in inputs.day_count.",
                    "Yield is an annual nominal rate compounded `frequency` times per year.",
                    "No credit/default or call risk is modelled; yield is promised yield to maturity."]
    return out


def main():
    p = argparse.ArgumentParser(description="Fixed-rate bond calculator (JSON out).")
    p.add_argument("--coupon", type=float, required=True, help="annual coupon, percent of face (e.g. 4.8)")
    p.add_argument("--maturity", required=True, help="YYYY-MM-DD")
    p.add_argument("--settlement", help="YYYY-MM-DD (default: today + 2 business days)")
    p.add_argument("--freq", type=int, default=2, choices=[1, 2, 4, 12], help="coupons per year")
    p.add_argument("--redemption", type=float, default=100.0, help="redemption per 100 face")
    p.add_argument("--basis", default="30/360", choices=["30/360", "act/act"], help="day count")
    p.add_argument("--price", type=float, help="CLEAN price, percent of face")
    p.add_argument("--yield", dest="yield_pct", type=float, help="annual yield, percent")
    p.add_argument("--shocks", type=lambda s: [float(x) for x in s.split(",")],
                   help="comma list of parallel yield shocks in bps, e.g. -100,-50,50,100")
    argv = sys.argv[1:]
    for i, tok in enumerate(argv[:-1]):      # let negative lists like -100,100 through argparse
        if tok == "--shocks":
            argv[i:i + 2] = ["--shocks=" + argv[i + 1]]
            break
    a = p.parse_args(argv)
    try:
        print(json.dumps(analyse(a), indent=2))
    except (ValueError, OverflowError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stdout)
        sys.exit(2)


if __name__ == "__main__":
    main()
