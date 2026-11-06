"""Coupled control on replicate 0: target world's mean over the logged anchor loans vs over all cohort loans."""
import sys, json
sys.path.insert(0, "src")
import numpy as np
from collection_simulator.config import load_config
from collection_simulator.generator import simulate_cohort
from ope_bench.panel import PI_FAR, action_id, balance_terciles, context_ids
out = {}
for seed in (9001, 9002, 9003):
    cfg = load_config("configs/tmlr/world_a_off.yaml"); cfg["seed"] = seed; cfg["population"]["borrowers"] = 1_000_000
    logs, _ = simulate_cohort(cfg, policy=None, replicate=0, batch_size=50_000)
    ctx = context_ids(logs, balance_terciles(logs))
    act = action_id(logs["channel_logged"], logs["discount_logged"])
    anc = logs["is_exploration"].to_numpy(bool) & (act == PI_FAR.actions_per_context()[ctx])
    tw, _ = simulate_cohort(cfg, policy=PI_FAR.generator_policy(), replicate=0, batch_size=50_000)
    assert np.array_equal(tw["loan_id"].to_numpy(), logs["loan_id"].to_numpy())
    rt = tw["reward"].to_numpy(np.float64)
    sd = rt.std(ddof=1)
    out[seed] = {"n_anchor": int(anc.sum()), "target_world_mean_all": float(rt.mean()),
                 "target_world_mean_on_anchors": float(rt[anc].mean()),
                 "z_anchor_subset": float((rt[anc].mean() - rt.mean()) / (sd / np.sqrt(anc.sum()))),
                 "logged_mean_on_anchors": float(logs["reward"].to_numpy()[anc].mean())}
    print(seed, {k: round(v, 2) for k, v in out[seed].items()}, flush=True)
json.dump(out, open("outputs/tmlr_revision_20261103/diagnostics/coupled_anchor_check_A_off_dev_seeds.json", "w"), indent=2)
