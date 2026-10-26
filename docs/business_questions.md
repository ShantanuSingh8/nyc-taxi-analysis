# Business framing (Phase 0)

## Stakeholder
**Primary:** a yellow-cab fleet operator deciding where and when to deploy drivers.
**Secondary:** NYC TLC, which regulates supply and pricing.

## Questions
1. **Demand:** Which zones and hours generate the most trips, and how does the weekday pattern differ from the weekend?
2. **Driver earnings:** Which zones, hours and trip types earn the most per hour of driving (fare ex-tip ÷ trip hours)?
3. **Tipping:** How does card tip % vary by borough, time of day, distance and airport vs city?
4. **Airports:** Are JFK/LGA trips worth the wait, comparing per-hour earnings with city trips?
5. **Pricing & platforms:** How big is the Flex Fare (upfront-priced) segment, how do its economics differ from metered trips, and how much of it is booked through Uber (`request_source = HV0003`, Jun 2026 onward)?

## Scope
- Yellow taxi, Jan–Jun 2026 (22.8M raw trips, 21.5M after cleaning)
- Out of scope for v1: FHV/FHVHV comparison and weather (stretch goals)

## Data notes found during profiling
- `payment_type = 0` is **Flex Fare** (~25% of trips). These rows have null `passenger_count`/`RatecodeID` by design, so they are flagged, not dropped.
- `request_source` first appears in the Jun 2026 file. Earlier months read it as NULL (`union_by_name`).
- `cbd_congestion_fee` is the MTA Congestion Relief Zone charge (since 5 Jan 2025).
- Cash tips are not recorded, so `tip_pct` is computed for card payments only.
