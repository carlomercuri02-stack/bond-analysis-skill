# Example of a finished answer

**Request:** "X.Y% bond maturing on DD/MM/YYYY, price Z. What does it yield and what if rates move?" (illustrative figures below: 4.8% coupon, matures 26 Feb 2027, price 100.00)

**Command run:**
`python3 scripts/bond_calc.py --coupon 4.8 --maturity 2027-02-26 --settlement 2026-11-12 --price 100.00 --shocks=-100,-50,50,100`

**Answer (shape to follow):**

Bottom line: at 100.00 the bond yields about 4.78% to maturity, and with under four months left it is almost insensitive to rates.

| Measure | Value |
|---|---|
| Clean price | 100.00 |
| Accrued interest | 1.013 |
| Dirty price | 101.013 |
| Yield to maturity | 4.78% |
| Current yield | 4.80% |
| Modified duration | 0.28 years |
| DV01 (per 100 face) | 0.0029 |

| Yield shock | New clean price | Change in value |
|---|---|---|
| +100 bp | 99.716 | -0.28% |
| +50 bp | 99.858 | -0.14% |
| -50 bp | 100.143 | +0.14% |
| -100 bp | 100.286 | +0.28% |

What it means: a one percentage point jump in yields costs roughly 0.28% of value, because almost the whole return is the final coupon plus principal arriving in a few months. The result is dominated by the issuer's credit and by FX if you hold it in another currency, which this calculation does not cover.

Assumptions: 30/360, settlement 12 Nov 2026, semi-annual coupons; credit and call risk not modelled.
(All figures come from the script's JSON; never retype them from memory.)

---

# Example: comparison (illustrative bonds, made-up terms, not real securities)

**Request:** "Compare a 3-year 3% corporate at 99.50 and a 5-year 3.5% BTP at 100.20, both EUR. ECB rate is 2.5%."

**Command run:**
`python3 scripts/bond_compare.py --ecb-rate 2.5 --settlement 2026-11-18 --invest 10000 --bond "isin=XX1,name=3y corporate,coupon=3,maturity=2029-11-15,price=99.5,currency=EUR,freq=1,type=corporate" --bond "isin=XX2,name=5y BTP,coupon=3.5,maturity=2031-11-15,price=100.2,currency=EUR,freq=1,type=btp"`

**Answer (shape to follow):**

Bottom line: held to maturity over the same five years, the 5-year BTP finishes ahead at about 3.41% a year against 2.92%, and it keeps the lead unless the ECB rate averages above roughly 3.9%.

| Bond | Maturity | Cost per 100 | Total return | Annualised | Years at ECB rate |
|---|---|---|---|---|---|
| 5y BTP | 15 Nov 2031 | 100.23 | 18.25% | 3.41% | 0 |
| 3y corporate | 15 Nov 2029 | 99.53 | 15.43% | 2.92% | 2 |

Profit on 10,000 invested in each bond (fees and taxes excluded):

| Bond | Final value | Profit vs not investing | Profit if left at the ECB rate | Extra profit vs ECB |
|---|---|---|---|---|
| 5y BTP | 11,825 | 1,825 | 1,328 | +497 |
| 3y corporate | 11,543 | 1,543 | 1,328 | +215 |

Breakeven: the 3-year bond only wins if its proceeds earn more than 3.89% a year for the final two years, against 2.50% assumed. Nothing here forecasts rates; it shows what you would have to believe for the ranking to flip.

Taxes are not modelled and a BTP is involved. Italian government bonds are taxed at 12.5% versus 26% for corporate bonds and deposit interest, which favours the BTP further, but check net returns before deciding.

Judgement, separate from the numbers: credit quality of the corporate issuer, liquidity and any call features are not in these figures.

Assumptions: both held to maturity, coupons and early proceeds reinvested at the ECB rate compounded monthly, fees excluded.
