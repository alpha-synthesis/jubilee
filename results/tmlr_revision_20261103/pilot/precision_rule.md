# Precision rule and cost ceiling — fixed before inspecting any pilot output

Recorded: 2026-11-03T19:53:26-03:00. At this time the pilot simulation was running and
no reference value, gap or estimator error of the pilot had been read.

Units: US$ per decision on the month-0 explorable cohort (reference values
range roughly 200–350 in the archived grid).

1. **Gaps.** For every pair of decision candidates (π_b, π_sms, π_visit,
   π_stage), the paired Monte-Carlo SE of the reference gap in a run must be
   at most **1.0**. Rationale: gaps below about 2 US$ (under 1% of a policy
   value) are not decision-relevant at this reward scale, and 1.96 × 1.0
   resolves every gap of 2 US$ or more; the archived gaps between candidates
   were 10–20 US$.
2. **Values.** The Monte-Carlo SE of every candidate's reference value in a
   run must be at most **2.0**, so the reference adds at most about 1% to the
   variance of the log-based errors (archived per-seed sd ≈ 20–27) and well
   under 1% for the pilots (≈ 55–70).
3. **R** (reference replicates of 1,000,000 borrowers per run) is the
   smallest number meeting 1–2 in every pilot condition (worst run), within
   the cost ceiling; if 1–2 cannot be met within the ceiling, the largest
   affordable R is used and unresolved rankings are reported as ambiguous.
4. **Cost ceiling** of the confirmatory campaign: **150 CPU-hours** on the
   existing server (simulation + estimation), about one night of wall time.
5. **Seeds**: 20 per condition as the budget hypothesis (error SE ≈ sd/√20);
   confirmation seeds 7001–7020, disjoint from development seeds 9001–9106.
   Coverage-type fractions over 20 seeds are reported as counts; no claim of
   interval calibration is made from them.
