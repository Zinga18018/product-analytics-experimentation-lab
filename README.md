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
- Explain the result in a concise business report.
- Present the findings in a Streamlit dashboard.

The dataset is synthetic and reproducible. It is designed for portfolio and interview practice, not for real business claims.

## Product Question

Does a redesigned onboarding experience improve the purchase conversion rate without hurting retention?

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
