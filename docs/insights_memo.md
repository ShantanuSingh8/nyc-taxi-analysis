# Memo: Where and when to deploy yellow-cab drivers

**To:** Fleet operations · **Data:** 21.5M cleaned NYC TLC yellow-taxi trips, Jan–Jun 2026

**Bottom line:** Fleet earnings depend more on *when* drivers are on the road than *where*. The biggest opportunities are closing a daily 4pm supply gap, pricing shifts by hourly earnings, and treating Uber as a core demand channel.

---

### 1. Shift change costs about 1 in 12 pickups at 4pm every weekday
Pickups fall 6–10% at 16:00 Monday to Friday, then rebound at 17:00, at the start of the busiest window of the week (Tue–Thu, 17:00–22:00, peaking at about 8,900 trips/hour Thursday 21:00). The dip doesn't happen on Saturday, which points to cabs off the road for shift change rather than riders staying home.
**Recommendation:** Stagger shift changes across 14:00–18:00 instead of clustering at 16:00. The dip averages about 550 trips; recovering half would add roughly 280 trips per weekday.

### 2. Day drivers earn about 30% less per hour than night drivers
Weekday earnings per meter-hour (fare + extra + tip) fall from about $104 at 1–4am to $72 at 15:00, as average speed drops from 17 mph to 8 mph. Earnings per trip barely change. Traffic, not trip quality, sets the rate.
**Recommendation:** Price day-shift and night-shift leases on earnings per meter-hour, not trip counts, so day drivers aren't overcharged relative to what the road lets them earn.

### 3. LaGuardia beats JFK, and both beat the city, before counting the queue
Airport trips earn $98–121 per meter-hour against $79 for city trips. LGA ($112–121) out-earns JFK ($98–103) because its trips are shorter and faster. The data doesn't record time spent in the airport taxi lot, which can cancel out the advantage for pickups.
**Recommendation:** Point drivers to LaGuardia over JFK. Before pushing more supply to either, measure queue times (e.g. from driver logs) to confirm the advantage survives the wait.

### 4. The payment screen, not the ride, sets the tip
53% of card riders tip exactly 20%, and most others pick 25%, 15%, 10%, 30% or 0%. Average tip % barely moves with borough, hour or distance (16.6–18.9%). Separately, one meter vendor records $0 tips on 97–100% of Bronx and Brooklyn card trips, either a data gap or lost driver income.
**Recommendation:** Work with meter vendors to test the preset tip options (e.g. leading with 20/25/30%), the strongest tip lever available. Audit Vendor 1's outer-borough tip records.

### 5. Uber now books almost a quarter of yellow-cab trips, and those trips pay more
Upfront-priced Flex Fare trips are 20–29% of trips each month. In June, the first month the booking channel was recorded, 92% of them came through Uber, 23% of all yellow trips. Flex trips earn 6% more per meter-hour than metered trips ($87.85 vs $82.96).
**Recommendation:** Treat Uber as a core demand channel, not a competitor. Keep drivers active on it, and track Flex share monthly as a key KPI.

---
*Method & caveats:* Earnings per meter-hour excludes time cruising empty, so it's an upper bound on real hourly pay. Tip analysis uses Vendor 2 card trips only, because cash tips aren't recorded. Full method, cleaning log and SQL are in the [README](../README.md).
