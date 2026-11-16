"""Run: python3 tests/test_bond_compare.py   (from the skill folder)"""
import json, subprocess, sys, pathlib
S = str(pathlib.Path(__file__).resolve().parent.parent / "scripts" / "bond_compare.py")

def run(*args, ok=True):
    r = subprocess.run([sys.executable, S, *args], capture_output=True, text=True)
    assert (r.returncode == 0) == ok, r.stdout + r.stderr
    return json.loads(r.stdout)

def close(a, b, tol):
    assert abs(a - b) <= tol, f"{a} != {b} (tol {tol})"

ZA = "coupon=0,maturity=2029-11-14,price=90,currency=EUR,name=A"   # zero coupon, 3y
ZB = "coupon=0,maturity=2031-11-14,price=80,currency=EUR,name=B"   # zero coupon, 5y
common = ["--settlement", "2026-11-14"]

# 1. Hand calc: A parks 100 for 730 days (24 months) at 2%, B pays 100 at horizon
r = run("--ecb-rate", "2", *common, "--bond", ZA, "--bond", ZB)
rows = {x["bond"]: x for x in r["ranking_at_input_rate"]}
tv_a = 100 * (1 + 0.02 / 12) ** 24
close(rows["A"]["terminal_value_per_100_face"], tv_a, 1e-4)
close(rows["A"]["total_return_pct"], (tv_a / 90 - 1) * 100, 1e-4)
close(rows["B"]["terminal_value_per_100_face"], 100.0, 1e-9)
assert rows["A"]["days_parked_at_ecb_rate"] == 730 and rows["B"]["days_parked_at_ecb_rate"] == 0

# 2. Breakeven: A and B level when (1+r/12)^24 = 90/80  ->  r = 1200*(1.125**(1/24)-1)
be = r["pairwise_breakeven"][0]
close(be["breakeven_reinvestment_rate_pct"], 1200 * (1.125 ** (1 / 24) - 1), 1e-3)
assert be["a_wins_when_rate_is"] == "above"
assert r["ranking_at_input_rate"][0]["bond"] == "B"      # at 2% B wins, below the breakeven

# 3. Different currencies are refused with a clear message
bad = run("--ecb-rate", "2", *common, "--bond", ZA, "--bond", ZB.replace("EUR", "USD"), ok=False)
assert "different currencies" in bad["error"]

# 4. BTP triggers the tax warning; an Italian ISIN without type=btp triggers the hint
w = run("--ecb-rate", "2", *common, "--bond", ZA + ",type=btp", "--bond", ZB)["warnings"]
assert any("TAXES NOT MODELLED" in x for x in w)
w = run("--ecb-rate", "2", *common, "--bond", ZA + ",isin=IT0005000000", "--bond", ZB)["warnings"]
assert any("Italian ISIN" in x for x in w)

# 5. Same maturity: no reinvestment dependence, no breakeven
r = run("--ecb-rate", "2", *common, "--bond", ZA, "--bond", ZA.replace("name=A", "name=C").replace("price=90", "price=91"))
assert r["pairwise_breakeven"][0]["breakeven_reinvestment_rate_pct"] is None
# 6. Profit figures: hand calc for the zero-coupon pair, 10,000 in each, ECB 2%, 1826 days
r = run("--ecb-rate", "2", *common, "--invest", "10000", "--bond", ZA, "--bond", ZB)
rows = {x["bond"]: x for x in r["ranking_at_input_rate"]}
ecb_alt = 10000 * ((1 + 0.02 / 12) ** (12 * 1826 / 365) - 1)
close(rows["A"]["profit_vs_not_investing"], 10000 * (tv_a / 90 - 1), 1e-3)
close(rows["B"]["profit_vs_not_investing"], 10000 * (100 / 80 - 1), 1e-3)
close(rows["A"]["profit_if_ecb_instead"], ecb_alt, 1e-3)
close(rows["B"]["excess_profit_vs_ecb"], 2500 - ecb_alt, 1e-3)
print("all 6 compare checks passed")
