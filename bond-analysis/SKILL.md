---
name: bond-analysis
description: Analyse and compare fixed-rate bonds with a verified calculator. Single bond - clean/dirty price, accrued interest, yield to maturity, duration, convexity, DV01, rate scenarios. Comparison - which of two or more bonds in the same currency pays more if held to maturity, including bonds with different maturities (shorter bond's proceeds reinvested at the ECB rate). Use whenever the user gives bond terms (coupon, maturity, price, yield, ISIN, BTP or corporate), asks what a bond yields or is worth, how rate-sensitive it is, or which bond to buy, even if they never say "duration", "YTM" or "compare".
---

# Bond analysis

The rule behind this skill: the scripts calculate every number, you interpret them. Language models make plausible-looking slips on discounting, day counts and reinvestment, so never compute price, yield, duration or returns yourself and never quote one from memory. A figure the user will act on has to be reproducible.

Two scripts live in `scripts/` (Python standard library only):
- `bond_calc.py` analyses ONE bond.
- `bond_compare.py` compares TWO OR MORE bonds held to maturity.

Choose by the request: one bond means Mode A, "which one" or several bonds means Mode B.

## Inputs checklist (both modes)

Before running a script, make sure every item below is settled. Missing inputs are the main source of wrong answers, and each one has a defined source:

| Input | Where it comes from |
|---|---|
| Clean price (or yield, Mode A) | Always the user. A live quote cannot be reliably looked up, so ask if it is missing. |
| ECB deposit rate (Mode B) | The user; otherwise the current ECB deposit facility rate from the ECB site. Say which you used, and if the user's rate differs from the current official rate, state both and call the user's figure an assumption. |
| Maturity, coupon, currency, coupon frequency, bond type | The user if given. If missing and an ISIN is available, look them up per `reference/isin_check.md` and show what you found for the user to confirm. If there is no ISIN and no way to look them up, ask. |
| Amount to invest in each bond (Mode B) | The user; default 10,000 in the bonds' currency, stated in the answer. |
| Settlement date | Quote date plus 2 business days; today plus 2 if no quote date is given. |

Ask for everything still missing in a single short message, not one question at a time. Never fill a gap by guessing, and never run the script on an assumed value without telling the user.

## Mode A: analyse one bond

1. Collect coupon (% of face), maturity date, and exactly one of clean price or yield. Settlement defaults to today + 2 business days; frequency 2, day count 30/360.
2. Run, always with shocks so the user sees rate sensitivity (write negative lists as `--shocks=-100,100`):
   ```
   python3 scripts/bond_calc.py --coupon 4.8 --maturity 2027-02-26 --settlement 2026-11-12 --price 100.00 --shocks=-100,-50,50,100
   ```
3. If the JSON has an `error`, fix the inputs and rerun. Do not fall back to mental arithmetic.
4. Answer in the format below. `reference/glossary.md` has the definitions; read it when the user is new to bonds.

## Mode B: compare bonds

What the comparison does: it fixes a common horizon (the latest maturity), reinvests every coupon and any early proceeds at the ECB deposit rate (monthly), and reports each bond's total and annualised return over that same horizon. A 3-year bond versus a 5-year bond therefore means "3-year bond plus 2 years at the ECB rate" against "5-year bond". No future bond price is forecast, because every bond is held to maturity. That is the point of the design: it keeps assumptions to a minimum, and the only open assumption (the reinvestment rate) is stress-tested by a breakeven.

Scope rules, and why:
- **One currency only.** FX moves are larger than typical yield gaps and would decide the ranking invisibly. If the bonds differ in currency, say so and stop; the script refuses as well.
- **Hold to maturity only.** Do not compare bonds "sold after N years" before maturity; the sale price would have to be guessed. If the user asks for that, explain that this skill does not do it, and offer to compare them held to maturity instead.
- **Taxes are not modelled.** The script warns when a BTP is involved (Italian government bonds are taxed at 12.5%, corporate bonds and deposit interest at 26%), and you must repeat that warning in the answer.

Steps:
1. **Collect per bond:** coupon, maturity date, clean price, currency, ISIN, and type (`btp`, `corporate` or `other`). Also ask how much the user would invest in each bond; if they give no amount, use 10,000 in the bonds' currency and say so. The ISIN is a label and a check; the maturity date must come from the user or the verified lookup.
   Coupon frequency (yearly or semi-annual) is read from the ISIN lookup in step 2 and the user does not need to state it. Ask only if the lookup does not return it, and never fall back to the semi-annual default without saying so: a wrong frequency changes the accrued interest, the cost and the cash flows.
2. **Verify against the ISIN.** Follow `reference/isin_check.md`. Report every mismatch before calculating, and say clearly when a bond could not be verified.
3. **Get the ECB deposit rate.** Use the figure the user gives; otherwise look up the current deposit facility rate on the ECB's key rates page. State which rate you used. If the user's figure differs from the current official rate (for example because they expect a hike), say so in the assumptions and note that the breakeven shows how much it matters.
4. **Run:**
   ```
   python3 scripts/bond_compare.py --ecb-rate 2.5 --settlement 2026-11-18 --invest 10000 \
     --bond "isin=XX1,name=3y,coupon=3,maturity=2029-11-15,price=99.5,currency=EUR,freq=1,type=corporate" \
     --bond "isin=XX2,name=5y,coupon=3.5,maturity=2031-11-15,price=100.2,currency=EUR,freq=1,type=btp"
   ```
   Use the same settlement date for all bonds, and use the quote date plus 2 business days if the user gave a quote date. Values in `--bond` must not contain commas.
5. **Answer in the compare format below.**

## Output format: single bond

Keep it under about 300 words unless asked for more.
1. **Bottom line** (1 to 2 sentences): yield and rate sensitivity.
2. **Numbers table:** clean price, accrued interest, dirty price, YTM, current yield, modified duration, convexity, DV01.
3. **Scenarios table:** shock, new price, exact % change. Mention the duration-only estimate only when it visibly differs from the exact value.
4. **What it means:** translate duration into money and compare with the user's alternative if they gave one. Describe the trade-off; do not tell them to buy or sell. Two points of accuracy:
   - Money figures come from the script's prices: loss on a face amount = (clean price minus `new_clean_price`) x face / 100. The `price_change_pct_exact` figure is measured against the dirty price, so applying it to the face value gives a slightly different (wrong) amount.
   - When the yield differs from the coupon, do not say accrued interest is the reason. Accrued interest comes back in the next coupon. The gap comes from the price relative to par and from the yield being a semi-annual compounded rate, which matters most in the last coupon period. Say that, or leave the gap unexplained.
5. **Assumptions and limits:** conventions used, and that credit and call risk are not modelled.

## Output format: comparison

1. **Bottom line** (1 to 2 sentences): which bond finishes ahead over which horizon, by how much (annualised), and how robust that is.
2. **Return table:** per bond: maturity, cost per 100 face, total return, annualised return over the common horizon, and days parked at the ECB rate.
3. **Profit table (always include):** for the amount invested in each bond, show the final value, the profit against not investing at all (`profit_vs_not_investing`), the profit the same cash would have earned at the ECB rate over the same period (`profit_if_ecb_instead`), and the extra profit over the ECB deposit (`excess_profit_vs_ecb`). Positive excess means the bond beat the deposit. Say the amount used and that fees and taxes are excluded.
4. **Breakeven:** from `pairwise_breakeven`, in one sentence per pair: "the shorter bond only wins if the reinvestment rate is above X%; the rate used is Y%". This is the robustness test; explain that nothing is being forecast, the user judges whether X is plausible.
5. **Warnings:** repeat every item in `warnings` (taxes, Italian ISIN hint, verification gaps).
6. **Judgement (clearly separate from the numbers):** credit quality, liquidity, call features, fees. No buy or sell instruction; the decision is the user's.
7. **Assumptions:** held to maturity, reinvestment at the ECB rate compounded monthly, fees and taxes excluded.

Accuracy rules for the comparison:
- Quote gaps between bonds by subtracting the script's figures exactly (for example 5.01 minus 3.36 is 1.65 points). Do not round first.
- If a bond is callable and priced above 100, say the ranking is an upper bound for that bond: if the issuer calls it at par, the real return can be lower, and the script does not model this.
- If the ECB rate the user gives differs from the current official deposit rate, mention both in one line. The breakeven shows whether it matters.

`reference/example_output.md` shows both formats finished. Do not quote the yield to maturity of bonds with different maturities as if it were comparable; the annualised return over the common horizon is the comparable figure.

## Limits

Fixed-rate bullet bonds only. No floaters, inflation-linked, callable or amortising bonds, ex-coupon periods or holiday calendars (weekends only). If the user's bond is one of these, say so rather than forcing it through. You are explaining numbers, not giving financial advice.
