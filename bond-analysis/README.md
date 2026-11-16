# bond-analysis (Claude skill)

Analyses and compares fixed-rate bonds. Python scripts calculate price, yield to maturity, duration, convexity, rate scenarios and held-to-maturity returns; Claude explains the results. Principle: the code calculates the numbers, the AI interprets them, so every figure can be checked.

## Folder layout
```
bond-analysis/
  SKILL.md                   instructions Claude follows
  scripts/bond_calc.py       one-bond calculator, CLI in / JSON out, stdlib only
  scripts/bond_compare.py    compares 2+ bonds held to maturity over a common horizon
  reference/isin_check.md    how Claude verifies inputs against the ISIN online
  reference/glossary.md      definitions (YTM, duration, convexity...)
  reference/example_output.md  what a finished answer looks like
  tests/                     test_bond_calc.py (6 checks), test_bond_compare.py (5 checks)
```

## Install
- **Claude Code**: copy the `bond-analysis` folder to `~/.claude/skills/` (all projects) or `<project>/.claude/skills/`.
- **Claude.ai / Cowork**: zip the `bond-analysis` folder (SKILL.md at the top of the zip folder) and upload it under Settings > Capabilities > Skills.
Requires Python 3.8+. No packages.

## Use
Ask in plain language: "X.Y% bond maturing on DD/MM/YYYY, price Z, what's the yield and what happens if rates rise 1%?" Claude loads the skill, runs the script and explains.

Direct use:
```
python3 scripts/bond_calc.py --coupon 4.8 --maturity 2027-02-26 --settlement 2026-11-12 --price 100 --shocks=-100,100
python3 scripts/bond_calc.py --coupon 5 --maturity 2036-01-15 --settlement 2026-01-15 --yield 6
```

## Comparing bonds
Ask "which of these bonds is better?" with coupon, maturity, price, currency and ISIN for each. The skill checks the data against the ISIN online, then compares all bonds over the latest maturity: each bond's coupons and any early proceeds are reinvested at the ECB deposit rate (monthly). Result: annualised return per bond over the same horizon, the profit on a stated amount against not investing and against leaving the same cash at the ECB rate (`--invest`, default 10,000), plus the breakeven reinvestment rate that would flip the ranking. Scope: one currency per comparison, bonds held to maturity (no forecast sale prices), taxes not modelled (a warning appears when a BTP is involved).
```
python3 scripts/bond_compare.py --ecb-rate 2.5 --settlement 2026-11-18 --bond "coupon=3,maturity=2029-11-15,price=99.5,currency=EUR,name=A" --bond "coupon=3.5,maturity=2031-11-15,price=100.2,currency=EUR,name=B,type=btp"
```

## Verify
Run `python3 tests/test_bond_calc.py` and `python3 tests/test_bond_compare.py`. The first checks a textbook price (5%, 10y, 6% yield = 92.5613), a par bond, a price-yield round trip, accrued interest by hand, convexity behaviour and error handling. For real bonds, the script was checked against Deutsche Boerse (Frankfurt) pages on 16 Nov 2026, using each page's own price and settlement date: yields agreed to within 1 basis point on both bonds tested. Duration figures differ slightly from the site's, probably a convention difference; the site does not say.

## Known limits
Fixed-rate bullet bonds only. Comparisons: one currency, held to maturity, taxes not computed, reinvestment at one constant rate (use the breakeven to judge it). No floaters, inflation-linked, callable or amortising bonds. No holiday calendar (weekends only). No credit or default risk: YTM is the promised yield. Yield is a nominal annual rate compounded at the coupon frequency.
