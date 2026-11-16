#!/usr/bin/env python3
"""
bond_compare.py - compare fixed-rate bonds held to maturity over a common horizon.

Method (no price forecasts needed):
  - Horizon = the latest maturity among the bonds.
  - Cost of each bond = clean price + accrued interest at settlement.
  - Every cash flow (coupons, principal) received before the horizon is
    reinvested at the ECB deposit rate, compounded monthly, until the horizon.
    A bond that matures early therefore "parks" its proceeds at the ECB rate.
  - Result per bond: terminal value, total return and annualised return over
    the same horizon, so bonds of different maturity are directly comparable.
  - Because the reinvestment rate is the one uncertain input, the script also
    reports the BREAKEVEN reinvestment rate for each pair of bonds: the rate at
    which the two finish level. No forecast is needed; compare it with today's.

Rules: all bonds must share one currency. Taxes are not modelled; a warning is
issued when a BTP is involved.

Usage:
  python bond_compare.py --ecb-rate 2.5 --settlement 2026-11-18 --invest 10000 \
    --bond "isin=XX1,name=A,coupon=3,maturity=2029-11-15,price=99.5,currency=EUR" \
    --bond "isin=XX2,name=B,coupon=3.5,maturity=2031-11-15,price=100.2,currency=EUR"
Bond fields (key=value, comma separated, no commas inside values):
  coupon, maturity (YYYY-MM-DD), price (clean, % of face), currency   required
  isin, name, freq (default 2), type (btp | corporate | other), basis (30/360 | act/act)
"""
import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bond_calc as bc  # noqa: E402


def parse_bond(spec, idx):
    kv = {}
    for part in spec.split(","):
        if "=" not in part:
            raise ValueError(f"bad --bond field {part!r}: use key=value pairs separated by commas")
        k, v = part.split("=", 1)
        kv[k.strip().lower()] = v.strip()
    for req in ("coupon", "maturity", "price", "currency"):
        if req not in kv:
            raise ValueError(f"--bond is missing '{req}': {spec}")
    btype = kv.get("type", "other").lower()
    if btype not in ("btp", "corporate", "other"):
        raise ValueError("type must be btp, corporate or other")
    basis = kv.get("basis") or ("act/act" if btype == "btp" else "30/360")
    if basis not in ("30/360", "act/act"):
        raise ValueError("basis must be 30/360 or act/act")
    isin = kv.get("isin", "")
    return {
        "label": kv.get("name") or isin or f"bond{idx}",
        "isin": isin, "type": btype, "basis": basis,
        "coupon": float(kv["coupon"]), "price": float(kv["price"]),
        "maturity": bc.parse_date(kv["maturity"]),
        "currency": kv["currency"].upper(), "freq": int(kv.get("freq", 2)),
    }


def payments(b, settlement):
    dates = bc.coupon_dates(b["maturity"], b["freq"])
    c = b["coupon"] / b["freq"]
    return [(d, c + (100.0 if d == b["maturity"] else 0.0))
            for d in dates if settlement < d <= b["maturity"]]


def growth(rate_pct, days):
    """Monthly compounding at an annual rate, over `days` calendar days."""
    return (1 + rate_pct / 1200) ** (12 * days / 365)


def terminal_value(cfs, horizon, rate_pct):
    return sum(amt * growth(rate_pct, (horizon - d).days) for d, amt in cfs)


def evaluate(b, settlement, horizon, rate_pct):
    flows, accrued, _ = bc.build_cashflows(b["coupon"], b["maturity"], settlement,
                                           b["freq"], 100.0, b["basis"])
    cost = b["price"] + accrued
    cfs = payments(b, settlement)
    tv = terminal_value(cfs, horizon, rate_pct)
    days = (horizon - settlement).days
    total = tv / cost - 1
    return {"cost": cost, "accrued": accrued, "tv": tv, "total": total,
            "annualised": (tv / cost) ** (365 / days) - 1,
            "ytm": bc.yield_from_dirty(flows, cost, b["freq"]),
            "cfs": cfs}


def breakeven(a, b, settlement, horizon):
    def diff(r):
        ea, eb = evaluate(a, settlement, horizon, r), evaluate(b, settlement, horizon, r)
        return ea["tv"] / ea["cost"] - eb["tv"] / eb["cost"]
    lo, hi = -5.0, 30.0
    dlo, dhi = diff(lo), diff(hi)
    if dlo * dhi > 0:
        return None, (a["label"] if dlo > 0 else b["label"]), None
    for _ in range(200):
        mid = (lo + hi) / 2
        dm = diff(mid)
        if dlo * dm <= 0:
            hi, dhi = mid, dm
        else:
            lo, dlo = mid, dm
    r = (lo + hi) / 2
    side = "above" if diff(r + 0.5) > 0 else "below"
    return r, None, side


def r6(x):
    return None if x is None else round(x, 6)


def compare(args):
    bonds = [parse_bond(s, i + 1) for i, s in enumerate(args.bond)]
    if len(bonds) < 2:
        raise ValueError("give at least two --bond entries")
    if len({b["currency"] for b in bonds}) > 1:
        raise ValueError("bonds are in different currencies ("
                         + ", ".join(sorted({b["currency"] for b in bonds}))
                         + "); this comparison only supports one currency, "
                           "because FX moves would swamp the yield differences")
    settlement = bc.parse_date(args.settlement) if args.settlement else bc.add_business_days(date.today(), 2)
    for b in bonds:
        if b["maturity"] <= settlement:
            raise ValueError(f"{b['label']} matures on or before settlement")
    horizon = max(b["maturity"] for b in bonds)
    days = (horizon - settlement).days
    labels = [b["label"] for b in bonds]
    if len(set(labels)) != len(labels):
        raise ValueError("bond names must be unique")

    def table(rate):
        rows = []
        for b in bonds:
            e = evaluate(b, settlement, horizon, rate)
            parked = max((horizon - b["maturity"]).days, 0)
            profit = args.invest * e["total"]                       # vs not investing at all
            ecb_alt = args.invest * (growth(rate, days) - 1)         # same cash left at the ECB rate
            rows.append({"bond": b["label"], "isin": b["isin"], "type": b["type"],
                         "maturity": b["maturity"].isoformat(),
                         "days_parked_at_ecb_rate": parked,
                         "cost_per_100_face": r6(e["cost"]), "ytm_pct": r6(e["ytm"]),
                         "terminal_value_per_100_face": r6(e["tv"]),
                         "total_return_pct": r6(e["total"] * 100),
                         "annualised_return_pct": r6(e["annualised"] * 100),
                         "invested": r6(args.invest),
                         "final_value": r6(args.invest * e["tv"] / e["cost"]),
                         "profit_vs_not_investing": r6(profit),
                         "profit_if_ecb_instead": r6(ecb_alt),
                         "excess_profit_vs_ecb": r6(profit - ecb_alt)})
        return sorted(rows, key=lambda r: -r["total_return_pct"])

    base = table(args.ecb_rate)
    scen = []
    for bp in args.rate_shocks:
        rate = args.ecb_rate + bp / 100
        rows = table(rate)
        scen.append({"reinvestment_rate_pct": r6(rate), "shock_bps": bp,
                     "winner": rows[0]["bond"],
                     "annualised_returns_pct": {r["bond"]: r["annualised_return_pct"] for r in rows}})

    pairs = []
    for i in range(len(bonds)):
        for j in range(i + 1, len(bonds)):
            a, b = bonds[i], bonds[j]
            r, always, side = breakeven(a, b, settlement, horizon)
            p = {"bond_a": a["label"], "bond_b": b["label"]}
            if r is None:
                p["breakeven_reinvestment_rate_pct"] = None
                p["result"] = f"{always} finishes ahead at every reinvestment rate tested (-5% to 30%)"
            else:
                p["breakeven_reinvestment_rate_pct"] = r6(r)
                p["a_wins_when_rate_is"] = side
                p["gap_vs_input_rate_pp"] = r6(args.ecb_rate - r)
                p["result"] = (f"{a['label']} finishes ahead if the reinvestment rate is {side} "
                               f"{r:.2f}%, otherwise {b['label']} does. Input rate: {args.ecb_rate:.2f}%.")
            pairs.append(p)

    warnings = []
    btps = [b["label"] for b in bonds if b["type"] == "btp"]
    if btps:
        warnings.append("TAXES NOT MODELLED. A BTP is involved (" + ", ".join(btps) + "). "
                        "Italian government bonds are taxed at 12.5% against 26% for corporate bonds "
                        "and deposit interest, so a net-of-tax comparison can rank the bonds differently. "
                        "Check net returns before deciding.")
    for b in bonds:
        if b["isin"].upper().startswith("IT") and b["type"] != "btp":
            warnings.append(f"{b['label']} has an Italian ISIN. If it is a BTP, set type=btp; "
                            "its tax treatment differs.")
    if len({b["maturity"] for b in bonds}) == 1:
        warnings.append("All bonds mature on the same date, so reinvestment assumptions do not affect the ranking.")

    return {
        "inputs": {"settlement": settlement.isoformat(), "horizon": horizon.isoformat(),
                   "horizon_days": days, "currency": bonds[0]["currency"],
                   "reinvestment_rate_pct": args.ecb_rate,
                   "reinvestment": "all coupons and early proceeds at the ECB rate, compounded monthly",
                   "invested_per_bond": args.invest},
        "ranking_at_input_rate": base,
        "sensitivity_to_reinvestment_rate": scen,
        "pairwise_breakeven": pairs,
        "warnings": warnings,
        "notes": ["All bonds are assumed held to maturity: no sale price is forecast.",
                  "Cost includes accrued interest at settlement. Fees and taxes are excluded.",
                  "The ECB rate is held constant until the horizon; breakevens show how much that matters.",
                  "ytm_pct is the bond's own yield to maturity and is not comparable across maturities; "
                  "use annualised_return_pct over the common horizon instead.",
                  "Credit and call risk are not modelled.",
                  "Profit figures assume the same cash amount in each bond, no fees, no tax, and fractional "
                  "face amounts (not rounded to tradable lots). profit_vs_not_investing = final value minus cash "
                  "invested; profit_if_ecb_instead = what the same cash earns at the ECB rate over the same "
                  "horizon; excess_profit_vs_ecb = the difference (positive means the bond beat the deposit)."],
    }


def main():
    p = argparse.ArgumentParser(description="Compare bonds held to maturity over a common horizon (JSON out).")
    p.add_argument("--bond", action="append", required=True, help="key=value,... see module docstring")
    p.add_argument("--ecb-rate", type=float, required=True, help="reinvestment rate, percent per year (ECB deposit rate)")
    p.add_argument("--settlement", help="YYYY-MM-DD (default today + 2 business days)")
    p.add_argument("--invest", type=float, default=10000.0,
                   help="cash amount put into EACH bond, in the bonds' currency (default 10000)")
    p.add_argument("--rate-shocks", default="-100,0,100", type=lambda s: [float(x) for x in s.split(",")],
                   help="reinvestment-rate shocks in bps for the sensitivity table")
    argv = sys.argv[1:]
    for i, tok in enumerate(argv[:-1]):
        if tok in ("--rate-shocks", "--ecb-rate"):
            argv[i:i + 2] = [tok + "=" + argv[i + 1]]
    a = p.parse_args(argv)
    try:
        print(json.dumps(compare(a), indent=2))
    except (ValueError, OverflowError, KeyError) as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(2)


if __name__ == "__main__":
    main()
