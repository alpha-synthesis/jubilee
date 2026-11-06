"""Fixed dictionaries for synthetic consumer-credit data generation.

Region labels are opaque codes; the geographic coordinates and population
weights are what drive the draws.
"""

from __future__ import annotations

LOCATIONS = [
    {"uf": "R01", "city": "Metro-01", "lat": -23.5505, "lon": -46.6333, "weight": 0.22},
    {"uf": "R02", "city": "Metro-02", "lat": -22.9068, "lon": -43.1729, "weight": 0.12},
    {"uf": "R03", "city": "Metro-03", "lat": -19.9167, "lon": -43.9345, "weight": 0.10},
    {"uf": "R04", "city": "Metro-04", "lat": -12.9777, "lon": -38.5016, "weight": 0.08},
    {"uf": "R05", "city": "Metro-05", "lat": -25.4284, "lon": -49.2733, "weight": 0.08},
    {"uf": "R06", "city": "Metro-06", "lat": -30.0346, "lon": -51.2177, "weight": 0.07},
    {"uf": "R07", "city": "Metro-07", "lat": -8.0476, "lon": -34.8770, "weight": 0.06},
    {"uf": "R08", "city": "Metro-08", "lat": -3.7319, "lon": -38.5267, "weight": 0.06},
    {"uf": "R09", "city": "Metro-09", "lat": -16.6869, "lon": -49.2648, "weight": 0.05},
    {"uf": "R10", "city": "Metro-10", "lat": -15.7939, "lon": -47.8828, "weight": 0.05},
    {"uf": "R11", "city": "Metro-11", "lat": -3.1190, "lon": -60.0217, "weight": 0.04},
    {"uf": "R12", "city": "Metro-12", "lat": -1.4558, "lon": -48.4902, "weight": 0.04},
    {"uf": "R13", "city": "Metro-13", "lat": -27.5954, "lon": -48.5480, "weight": 0.03},
]

GENDERS = ["female", "male", "non_binary", "not_informed"]

INCOME_BANDS = [
    {"band": "B1", "min": 1400.0, "max": 2800.0, "weight": 0.26},
    {"band": "B2", "min": 2800.0, "max": 5600.0, "weight": 0.34},
    {"band": "B3", "min": 5600.0, "max": 11200.0, "weight": 0.24},
    {"band": "B4", "min": 11200.0, "max": 21000.0, "weight": 0.11},
    {"band": "B5", "min": 21000.0, "max": 42000.0, "weight": 0.05},
]

PRODUCTS = [
    {"product_type": "cartao_credito", "term_months": 24, "rate": 0.035, "weight": 0.34},
    {"product_type": "credito_pessoal", "term_months": 36, "rate": 0.028, "weight": 0.28},
    {"product_type": "veiculo", "term_months": 48, "rate": 0.022, "weight": 0.16},
    {"product_type": "consignado", "term_months": 60, "rate": 0.017, "weight": 0.14},
    {"product_type": "renegociacao", "term_months": 30, "rate": 0.025, "weight": 0.08},
]

CHANNELS = ["none", "sms", "app_message", "phone", "field_visit"]

PUBLIC_TABLES = ["borrowers", "loans", "actions", "monthly_panel"]

TERMINAL_STATES = {"cured", "charged_off"}
ALLOWED_STATES = {"performing", "delinquent", "credito_em_liquidacao", *TERMINAL_STATES}
