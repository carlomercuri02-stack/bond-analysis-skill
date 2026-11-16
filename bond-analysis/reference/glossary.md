# Glossary

- **Clean price**: quoted price, % of face, without accrued interest. What screens and brokers show.
- **Accrued interest**: coupon earned by the seller since the last coupon date, paid by the buyer on top of the clean price.
- **Dirty price**: clean + accrued. The cash that actually changes hands per 100 face.
- **Current yield**: annual coupon / clean price. Ignores gain or loss to maturity.
- **Yield to maturity (YTM)**: the single annual rate that discounts all remaining cash flows to the dirty price. Assumes you hold to maturity, coupons are reinvested at the same rate and the issuer pays. Quoted here as a nominal annual rate compounded at the coupon frequency.
- **Macaulay duration**: the weighted-average time (years) until you receive the cash flows, weighted by their present value.
- **Modified duration**: Macaulay / (1 + y/f). Approximate % price change for a 1 percentage point (100 bp) move in yield: price change % ≈ -modified duration x yield change.
- **Convexity**: how much that duration estimate curves. Positive convexity means prices rise more when yields fall than they drop when yields rise by the same amount. It matters for big shocks and long bonds; for a bond near maturity it is negligible.
- **DV01**: money change in dirty price (per 100 face) for a 1 bp yield move.
- **Day count 30/360**: each month counts as 30 days, year as 360. Standard for US corporate bonds.
- **Settlement (T+2)**: the date cash and bond change hands, two business days after the trade date for US corporates. Prices and accrued interest are computed to this date.

Rule of thumb: as maturity shrinks, price converges to the redemption value and duration to the time left, so a bond a few months from maturity barely reacts to rate changes.
