# Bond analysis skill for Claude

A Claude skill that analyses and compares fixed-rate bonds. Claude does the reading and explaining, and a small Python script does every calculation, so the numbers are reproducible and checkable.

## What it does

- **Single bond:** clean and dirty price, accrued interest, yield to maturity, duration, convexity, DV01, and what happens to the price if rates move.
- **Comparison of two or more bonds in the same currency:** all bonds are held to maturity over the latest maturity. Coupons and the proceeds of shorter bonds are reinvested at the ECB deposit rate, compounded monthly. The output shows the annualised return per bond, the profit on a stated amount against not investing and against leaving the same cash at the ECB rate, and the reinvestment rate at which the ranking flips.
- **ISIN check:** Claude verifies coupon, maturity, currency and coupon frequency online before running the numbers.

Taxes are not modelled. A warning appears when an Italian government bond (BTP) is involved.

## Install

1. Download `bond-analysis.zip` from the latest release.
2. In Claude, open Settings, then Capabilities, then Skills, and upload the zip.
3. Ask, for example: "Compare these two bonds: coupon, maturity, price, currency and ISIN for each."

In Claude Code, copy the `bond-analysis` folder into `.claude/skills/` instead.

## Run the script without Claude

```
python3 bond-analysis/scripts/bond_calc.py --coupon 3 --maturity 2029-11-15 --settlement 2026-11-18 --price 99.5
python3 bond-analysis/scripts/bond_compare.py --ecb-rate 2.5 --settlement 2026-11-18 \
  --bond "coupon=3,maturity=2029-11-15,price=99.5,currency=EUR" \
  --bond "coupon=3.5,maturity=2031-11-15,price=100.2,currency=EUR"
```

Python 3 standard library only, no installs needed. Tests: `python3 bond-analysis/tests/test_bond_calc.py` and `python3 bond-analysis/tests/test_bond_compare.py`.

## Limits

Fixed-rate bonds only, one currency per comparison, held to maturity, no credit or call risk, fees and taxes excluded. The ECB rate is assumed constant until the horizon, and the breakeven shows how much that assumption matters. This is a calculation aid, not investment advice.

## Licence

MIT, see `LICENSE`.
