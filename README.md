# Product Analytics Experimentation Lab

[See the workflow flowchart and code walkthrough](WORKFLOW.md)

End-to-end product analytics project for data analyst, product data science, and applied ML internship roles.

## What This Project Shows

This project simulates the work of a product data analyst or product data scientist:

- Define product questions.
- Generate and store event-level product data in SQLite.
- Query data with SQL.
- Build funnel, cohort retention, and revenue metrics.
- Evaluate an A/B test with a two-proportion z-test.
- Require complete follow-up, check assignment balance, and quantify uncertainty.
- Block rollout when retention or revenue noninferiority is not established.
- Explain the result in a concise business report.
- Present the findings in a Streamlit dashboard.

The dataset is synthetic and reproducible. It is designed for portfolio and interview practice, not for real business claims.

## Product Question

Does a redesigned onboarding experience improve purchase conversion while keeping retention and revenue losses within declared tolerances?

The answer now comes from one shared decision function used by the report and dashboard. Statistically significant conversion improvement alone cannot approve rollout. [See four constructed stress scenarios](outputs/guardrail_scenarios.md), including conversion gains that fail retention, revenue or assignment checks.

## Project Structure

```text
product_analytics_experimentation_lab/
  app.py                         # Streamlit dashboard
  src/
    data_generator.py             # deterministic synthetic data generator
    analytics.py                  # SQL-backed metrics and statistics
    reporting.py                  # markdown report generation
  scripts/
    build_dataset.py              # creates SQLite database
    run_analysis.py               # creates markdown report
  sql/
    product_metrics.sql           # interview-style SQL queries
  tests/
    test_analytics.py             # core tests
  data/
    product_analytics.sqlite      # generated locally
  outputs/
    analysis_report.md            # generated locally
```

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python scripts\build_dataset.py
python scripts\run_analysis.py
python scripts\run_guardrail_scenarios.py
streamlit run app.py
```

## Test

```powershell
python -m unittest discover tests
```

## Metrics Produced

The pipeline creates:

- user, session, event, and experiment-assignment tables
- landing-to-purchase funnel by experiment variant
- purchase conversion lift
- two-proportion z-test p-value
- acquisition-channel performance
- 7-day, 14-day, and 30-day cohort retention
- exact binomial sample-ratio checks for enrolled and fully observed cohorts
- conversion and retention difference intervals (Newcombe/Wilson)
- revenue per assigned user and a Welch t interval
- an explicit hold/review decision with every failed gate listed

## Metric Contract and Decision Policy

[config/experiment_policy.json](config/experiment_policy.json) records the illustrative settings before analysis. The default synthetic data cutoff is March 2, 2026 (exclusive UTC). Change the declared cutoff for a different dataset; it is not inferred from the last event.

| Metric | Definition | Denominator |
| --- | --- | --- |
| Conversion | At least one purchase in `[assignment, assignment + 7 days)` | Every assigned user with the complete 8-day common follow-up horizon |
| Retention guardrail | Any session during days 1-7, `[assignment + 1 day, assignment + 8 days)` | The same mature assigned users, including inactive users |
| Revenue guardrail | Sum of purchase revenue in the first 7 days | The same mature assigned users, including non-purchasers |
| Signup cohort retention | Any activity in days 1-7, 8-14, or 15-30 | All signup users with complete follow-up for that particular window |

The example policy requires at least 100 users per arm, expected 50/50 assignment, SRM p-values of at least 0.001, conversion significance at 0.05 plus a positive lower difference bound, retention's lower bound above -2 percentage points, and revenue's lower bound above -1 synthetic currency unit per user. These are **configurable demonstration settings, not an asserted business policy or a power analysis**. Do not tune tolerances after seeing results. Passing every gate means eligible for a staged rollout *review*.

[The generated report](outputs/analysis_report.md) records denominators, cutoff, policy, intervals and blockers. [The JSON readout](outputs/experiment_readout.json) preserves full numerical precision. Sparse conversion counts, missing arms, empty cohorts and unavailable revenue uncertainty produce a hold; duplicate assignments/events or invalid input data raise validation errors.

## Resume-Ready Framing

Use this project to show:

- SQL: CTEs, joins, aggregations, cohort queries
- Python: reproducible pipeline, data validation, statistical testing
- Product analytics: funnel, retention, conversion, experiment readout
- Dashboarding: Streamlit KPI dashboard

## Limitations

- Synthetic data only.
- No causal claim beyond the simulated experiment design.
- Not deployed yet.
- Dashboard is intentionally lightweight so the analysis remains the main focus.
- Fixed-horizon, two-arm, user-randomized design. Repeated peeking and exploratory segments require a separate analysis plan.
- The signup retention metrics are activity windows, not exact-day retention. Late cohorts have unavailable values until fully observed.
- Revenue intervals use Welch's approximation and may be unreliable for severe heavy tails. Both-zero revenue variance blocks the revenue gate.
- Acquisition-channel comparisons use all observed time and are descriptive, not causal or part of the rollout decision.
- No actual customer deployment, business lift, or prospective policy validation is claimed.

## Statistical References

- [Newcombe (1998), independent-proportion difference intervals](https://pubmed.ncbi.nlm.nih.gov/9595617/) explains the Wilson-based interval approach.
- [SciPy binomtest](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html) provides the exact assignment-balance test and Wilson interval test oracle.
- [SciPy independent-sample testing](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_ind.html) documents Welch testing and difference confidence intervals used as the revenue test oracle.
