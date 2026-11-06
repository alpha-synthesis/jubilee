# Collections Loan Book — Data Dictionary

This document describes the **exported dataset** (the public tables `borrowers`,
`loans`, `actions`, `monthly_panel`). It is written for an external analyst reading
the data as if it were a real bank's **collections / debt-recovery** book: a portfolio
of loans that are late or in recovery, the monthly contact actions the bank takes on
them, and how each loan evolves month to month.

Everything below describes only what is **observable in the exported data** and the
mechanical loan dynamics behind it (how a balance grows, how delinquency advances,
when an account cures or is charged off). It does **not** describe how outcomes are
decided internally — from this dataset's point of view, a payment either happened in a
given month or it did not.

- **Currency:** all monetary amounts are in **US$**. The world is synthetic and
  no parameter is calibrated to any real portfolio, so the unit fixes a scale
  rather than a market.
- **Time:** `month` is a 0-based index into the observation window (0 … 23 for a
  24-month export). Month 0 is the first observed month.
- **Grain:**
  - `borrowers` — one row per borrower.
  - `loans` — one row per loan (a loan's state *as observed at the start of the window*).
  - `actions` — one row per loan **per observed month**, until the loan resolves.
  - `monthly_panel` — one row per loan **per observed month**, until the loan resolves.
- **Join keys:** `borrower_id`, `loan_id`, and `(loan_id, month)`.

---

## 1. `borrowers`

One row per borrower — static demographic and location attributes.

| Column | Type | Meaning (external view) | How it is derived |
|---|---|---|---|
| `borrower_id` | string | Unique borrower identifier, e.g. `B000001`. | Sequential. |
| `uf` | string | Opaque region code, e.g. `R01`, `R07`. | Drawn from a fixed list of 13 metros, weighted toward the largest (top metro ≈ 22%). |
| `city` | string | City of residence (state capital). | Tied to `uf`. |
| `lat`, `lon` | float | Geographic coordinates of the city. | **City centroid** — every borrower in the same city shares identical coordinates; this is a city locator, not a household address. |
| `age` | int | Borrower age in years. | Centered near 42, spread ~13 years, clipped to [18, 78]. |
| `gender` | string | `female` / `male` / `non_binary` / `not_informed`. | ~49% female, ~49% male, ~1% each of the other two. |
| `income_band` | string | Declared income band, five ordered levels `B1` (lowest) through `B5`. | Most borrowers fall in the lower-middle bands (`B2` ≈ 34%). |
| `monthly_income` | float (US$) | Declared monthly income. | A value within the band's range, e.g. `B1` → 1,400–2,800. |
| `dependents` | int | Number of dependents. | Typically 0–2, capped at 5. |

---

## 2. `loans`

One row per loan, describing the loan's terms and its **delinquency snapshot at the
start of the observation window**. In this export each borrower has exactly one loan.

| Column | Type | Meaning (external view) | How it is derived |
|---|---|---|---|
| `loan_id` | string | Unique loan identifier, e.g. `L000001`. | Sequential. |
| `borrower_id` | string | Owning borrower (FK → `borrowers`). | — |
| `product_type` | string | Credit product: `cartao_credito` (credit card), `credito_pessoal` (personal loan), `veiculo` (auto), `consignado` (payroll-deducted), `renegociacao` (renegotiated debt). | Weighted; credit card is the most common (~34%). |
| `origination_month` | int | When the loan was originated, **relative to the start of the observation window**. Negative = originated before the window opened. E.g. `-7` = opened 7 months earlier. | `−loan_age_months`. |
| `original_principal` | float (US$) | Original disbursed amount of the loan. | Ranges roughly 800 – 60,000, skewed toward smaller loans. Fixed for the life of the loan. |
| `outstanding_balance` | float (US$) | Amount owed **at the start of the window** (the opening snapshot). | Between 45% and 105% of `original_principal` — i.e. a loan may owe slightly more than it borrowed once arrears/fees are folded in. The **evolving** balance month-to-month lives in `monthly_panel`. |
| `interest_rate_monthly` | float | Contractual monthly interest rate. | Fixed per product: e.g. credit card 3.5%/mo, payroll-deducted 1.7%/mo. |
| `term_months` | int | Original contractual term. | Fixed per product (24–60 months). |
| `loan_age_months` | int | Months elapsed since origination, **at the start of the window**. | Between 1 and `term_months`. |
| `remaining_maturity_months` | int | Contractual months left, at the start of the window. | `max(term_months − loan_age_months, 0)`. |
| `days_past_due` | int | Days overdue at the start of the window. | Centered around ~55 days, never negative. This is a **collections** book, so most loans open already late. |
| `days_in_credito_em_liquidacao` | int | Days the loan has been in the *credito em liquidação* (write-off/recovery) stage at the start of the window. | `max(days_past_due − 90, 0)` — a loan enters this stage after 90 days overdue. |
| `initial_status` | string | Delinquency status at the start of the window. | Derived from `days_past_due`: <30 → `performing`, 30–89 → `delinquent`, ≥90 → `credito_em_liquidacao`. |

---

## 3. `actions`

One row per loan **per observed month**: the contact/collection action the bank took
that month, and any settlement it offered. Rows stop once the loan resolves (see
*Loan lifecycle* below).

| Column | Type | Meaning (external view) | How it is derived |
|---|---|---|---|
| `action_id` | string | Unique action identifier, e.g. `A00000001`. | Sequential. |
| `loan_id` | string | Loan acted on (FK → `loans`). | — |
| `month` | int | Observation month (0-based). | — |
| `channel` | string | Contact channel used this month: `none` (no contact), `sms`, `app_message`, `phone`, `field_visit`. | More delinquent accounts tend to receive more intensive contact (phone, field visit); lighter or no contact is more common on fresher accounts. |
| `discount_offer` | float | Fractional discount offered on the outstanding balance this month, `0`–`0.55` (0–55%). `0` when no settlement is offered (e.g. `channel = none`). | A modest offer for most accounts, escalating for deeply delinquent ones (accounts past ~60 days overdue get progressively deeper discounts). |
| `settlement_offer_amount` | float (US$) | The lump sum the bank offers to **close the account** this month ("pay this and we consider the debt settled"). | `settlement_offer_amount = (start-of-month balance) × (1 − discount_offer)`. ⚠️ The balance used is the balance *entering* the month — i.e. the **prior** month's `outstanding_balance` (or the loan's opening balance in month 0), **not** the same-row `monthly_panel.outstanding_balance`, which is the end-of-month figure. See *Reconstructing the discount* below. |
| `is_exploration` | bool | Whether this month's action was an **ε-floor exploration** draw rather than the incumbent policy. Present only when generated with `actions.exploration`. | `True` with probability ε, applied only in active states (delinquent / early credito_em_liquidacao). Explored actions use a **uniformly random** contact channel and a **uniform** discount in `[0, max_discount]`. |
| `exploration_epsilon` | float | The exploration probability ε in force for this loan-month (`0` where the state was not explorable). | Lets an OPE estimator reconstruct the logging-policy propensity for the explored subset: `ε × (1/#contact_channels) × (1/max_discount)`. |

---

## 4. `monthly_panel`

One row per loan **per observed month**: the loan's state and balance as it evolves.
This is the table that shows the loan **dynamics**. Rows stop once the loan resolves.

| Column | Type | Meaning (external view) | How it is derived / evolves |
|---|---|---|---|
| `loan_id` | string | Loan (FK). | — |
| `borrower_id` | string | Borrower (FK). | — |
| `month` | int | Observation month (0-based). | — |
| `status` | string | Delinquency state **at the start of the month** (before this month's events). | One of `performing`, `delinquent`, `credito_em_liquidacao`, `cured`, `charged_off`. |
| `next_status` | string | State **at the end of the month** (after this month's payment/non-payment). | The loan's last observed row carries a terminal `next_status` (`cured` or `charged_off`). |
| `loan_age_months` | int | Loan age this month. | Advances by 1 each month over the window (opening age + `month`). |
| `remaining_maturity_months` | int | Contractual months remaining this month. | Decreases by 1 each month, floored at 0. |
| `days_past_due` | int | Days overdue this month. | **Grows by 30 each month the loan is not paid; resets to 0 the month a payment is collected.** |
| `days_in_credito_em_liquidacao` | int | Days in the write-off/recovery stage. | Starts accumulating (in 30-day steps) once `days_past_due` reaches 90. |
| `outstanding_balance` | float (US$) | Amount owed **at the end of the month** (after this month's events). | See *How the balance moves* below. |
| `contacts_last_3m` | int | A running count of months in which the borrower was contacted, **capped at 3**. | Increments by 1 each month a contact was made (any channel except `none`); holds at 3 thereafter. Note: it does **not** decay — despite the name it is a capped cumulative counter, not a strict rolling 3-month window. Values 0–3. |
| `action_id` | string | The action taken this month (FK → `actions`). | One action per loan-month. |
| `recovered` | bool | **Did the borrower pay anything toward this loan this month?** | The core monthly outcome of a collections book. |
| `charged_off` | bool | Was the loan written off (declared a loss) this month? | A terminal event; only happens to loans deep in the recovery stage. |
| `recovered_amount` | float (US$) | Amount actually collected this month. | `0` when `recovered = false`. When a payment is collected the borrower pays the agreed **settlement** (`balance × (1 − discount)`), mostly in full and occasionally partial — so `recovered_amount = settlement_offer_amount × paid_share` with `paid_share ≤ 1`, and it never exceeds the settlement offered. A bigger discount therefore **lowers** what is collected (a giveaway). The collected amount is subtracted from the balance. |

---

## Loan lifecycle & dynamics

This section answers the "how does it move" questions an analyst will have.

### States and transitions

A loan occupies one of five states:

| State | Meaning |
|---|---|
| `performing` | Current / not materially overdue (<30 days). |
| `delinquent` | 30–89 days overdue. |
| `credito_em_liquidacao` | ≥90 days overdue — moved to the write-off/recovery stage. |
| `cured` | **Terminal.** The loan was paid down enough to be considered resolved/good. |
| `charged_off` | **Terminal.** The loan was written off as a loss. |

Each observed month, exactly one of three things happens:

1. **Payment collected** (`recovered = true`) → some amount is collected, the balance
   drops, `days_past_due` resets to 0. If the remaining balance is small enough (below
   ~5% of original principal, minimum 50), the loan is **cured** (terminal);
   otherwise it returns to `performing`.
2. **Written off** (`charged_off = true`) → the loan becomes `charged_off` (terminal).
   This only happens to loans already deep in the `credito_em_liquidacao` stage.
3. **Nothing collected** → the loan rolls forward: `days_past_due += 30`, the balance
   accrues (below), and the status advances (`performing` → `delinquent` →
   `credito_em_liquidacao`) as the overdue days cross 30 and 90.

Once a loan reaches a terminal state it generates **no further rows** — its last
`monthly_panel` row shows the terminal value in `next_status`. So loans drop out of the
panel over time, and the surviving population grows more delinquent on average.

### How the balance moves — yes, it grows

- **When the loan is not paid in a month, the outstanding balance grows.** It accrues at
  roughly **35% of the contractual monthly rate** (`interest_rate_monthly × 0.35`) — a
  partial accrual reflecting that distressed/late accounts don't compound at the full
  contractual rate but still accumulate interest and fees. Example: a credit-card loan
  (3.5%/mo) grows ~1.2%/month while unpaid.
- **When a payment is collected, the balance drops** by `recovered_amount` (which can be
  a partial payment). A large enough paydown cures the loan.
- The opening balance (`loans.outstanding_balance`) can itself exceed
  `original_principal` (up to 105%), reflecting arrears already capitalized before the
  window opened.

Net effect: an unpaid loan's balance drifts **upward** month over month until it either
receives a payment, is charged off, or the observation window ends.

### Contact and settlement behavior

- The **channel** escalates with delinquency: deeply overdue accounts are more likely to
  get phone calls and field visits; fresher accounts get lighter touch or none.
- The **discount offer** escalates too: accounts past ~60 days overdue receive
  progressively deeper settlement discounts (up to the 55% cap).
- The **settlement offer** is always quoted against the balance *entering* the month.

### Reconstructing the discount from a flat export

Because `settlement_offer_amount` uses the start-of-month balance but
`monthly_panel.outstanding_balance` is the **end-of-month** balance, do **not** divide
them within the same row. Use the prior month's balance:

```
discount_offer[m] = 1 − settlement_offer_amount[m] / outstanding_balance[m−1]
```

(For month 0, use `loans.outstanding_balance` as the m−1 balance.) This identity holds
exactly across the dataset. Note also that the settlement is a fraction of the
**balance**, never of `original_principal`.

---

## Notes & gotchas

- **Collections book, not originations.** Loans open already overdue; the data describes
  the *recovery* phase, not healthy repayment.
- **Survivorship.** Loans leave the panel when they cure or charge off, so later months
  over-represent harder, unresolved accounts.
- **`contacts_last_3m` is a capped cumulative counter** (0–3), not a true 3-month rolling
  window — it never decreases.
- **`lat`/`lon` are city centroids**, shared by everyone in a city — usable for
  region-level analysis, not for household geolocation.
- **One loan per borrower** in this particular export (`loans_per_borrower = 1`).
