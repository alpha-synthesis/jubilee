from collection_simulator.config import load_config


def test_load_config_merges_defaults():
    cfg = load_config("configs/tiny_ci.yaml")
    assert cfg["population"]["borrowers"] == 40
    assert cfg["actions"]["max_discount"] > 0
    assert cfg["demographics"]["age_min"] == 18
