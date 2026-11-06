Origin of the post hoc accounting sensitivity (kept for disclosure; not part of the analysis pipeline).

decompose.py, analyze.py: an internal reviewer's read-only check, run after the main results on five
development pairs (A_on seeds 9301-9303 and B_on seeds 9301-9302, replicate 2). It re-ran the generator's
loop through its internal functions, kept the per-month records, and reproduced the pilot's benchmark
values to six decimals. It found that charging the discount of the recovery month or valuing cash
collected reverses the sign of the exploration effect (about -3.1 to -4.3 US$ per decision on those pairs).
That finding prompted protocol/protocol_sensitivity.json and scripts/exploration_effect_accounting.py,
which compute the same accountings on the 40 main pairs. The reviewer's per-pair arrays are not kept.

final_review_mech.py: a second reviewer's small diagnostic (seed 7001, replicate 2, 200,000 borrowers,
both worlds) used to check the mechanism statements; its figures are indicative only and are not quoted
as results.
