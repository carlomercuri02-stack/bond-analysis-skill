"""Run: python3 tests/test_bond_calc.py   (from the skill folder)"""
import json, subprocess, sys, pathlib
S = str(pathlib.Path(__file__).resolve().parent.parent / "scripts" / "bond_calc.py")

def run(*args):
    return json.loads(subprocess.check_output([sys.executable, S, *args]))

def close(a, b, tol):
    assert abs(a - b) <= tol, f"{a} != {b} (tol {tol})"

# 1. Textbook: 5% 10y semi-annual at 6% yield -> price 92.5613, mod. duration 7.665
r = run("--coupon", "5", "--maturity", "2036-01-15", "--settlement", "2026-01-15", "--yield", "6")
close(r["clean_price"], 92.5613, 1e-3); close(r["modified_duration_years"], 7.665, 1e-2)
# 2. Par bond yields its coupon
r = run("--coupon", "4", "--maturity", "2031-06-30", "--settlement", "2026-06-30", "--price", "100")
close(r["ytm_pct"], 4.0, 1e-6)
# 3. Price -> yield -> price round trip
r1 = run("--coupon", "3.25", "--maturity", "2034-09-12", "--settlement", "2026-11-12", "--price", "91.4")
r2 = run("--coupon", "3.25", "--maturity", "2034-09-12", "--settlement", "2026-11-12", "--yield", str(r1["ytm_pct"]))
close(r2["clean_price"], 91.4, 1e-4)
# 4. Accrued matches hand calc for a 4.8% bond maturing 26-Feb-2027 settled 12-Nov-2026: 2.4 * 76/180
r = run("--coupon", "4.8", "--maturity", "2027-02-26", "--settlement", "2026-11-12", "--price", "100")
close(r["accrued_interest"], 2.4 * 76 / 180, 1e-6)
# 5. Convexity makes the estimate better than duration alone for a +-100bp move
r = run("--coupon", "5", "--maturity", "2036-01-15", "--settlement", "2026-01-15", "--yield", "6", "--shocks=-100")
s = r["scenarios"][0]
assert abs(s["price_change_pct_exact"] - s["price_change_pct_duration_plus_convexity"]) < abs(s["price_change_pct_exact"] - s["price_change_pct_duration_only"])
# 6. Bad input reports an error
bad = subprocess.run([sys.executable, S, "--coupon", "4", "--maturity", "2020-01-01", "--settlement", "2026-01-01", "--price", "100"], capture_output=True, text=True)
assert bad.returncode == 2 and "error" in bad.stdout
print("all 6 checks passed")
