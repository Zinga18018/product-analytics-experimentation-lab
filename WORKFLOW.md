# Product Analytics Experimentation Lab: workflow

Use a synthetic product dataset to practice SQL metrics, funnel analysis, retention summaries and an experiment readout.

**Relevant roles:** data analyst, product data science.

## Flowchart

```mermaid
flowchart TD
A["Seeded synthetic users, sessions and events"] --> B["Store tables and indexes in SQLite"]
    B --> C["Validate assignment and event integrity"]
    P["Declared cutoff, windows and tolerances"] --> C
    C --> D["One row per fully observed assigned user"]
    D --> E["Conversion and retention intervals; revenue uncertainty"]
    B --> S["Enrolled and eligible sample-ratio checks"]
    E --> G{"All sample, conversion and guardrail gates pass?"}
    S --> G
    G -->|Yes| R["Eligible for staged rollout review"]
    G -->|No| H["Hold with explicit reasons"]
    R --> F["Shared dashboard and written readout"]
    H --> F
```

## Explain it in an interview

“I start with the product question and declare the observation windows and tolerated losses. SQL keeps inactive users in the denominator and excludes users who have not had enough follow-up. I then check assignment balance, conversion uncertainty and retention/revenue guardrails. A conversion gain can still produce a hold.”

## What this diagram does and does not establish

The dataset and stress scenarios are synthetic, so estimated lifts are not business outcomes. Retention is activity within a window, not exact-day retention. All gates are enforced, but policy values are illustrative and require advance agreement for a real experiment. Statistical intervals assume independent user assignment and a fixed analysis horizon; they do not correct for repeated peeking or severe revenue heavy tails.

## Follow the code

- [Synthetic tables and database](src/data_generator.py)
- [SQL metrics, retention and experiment test](src/analytics.py)
- [Report and recommendation logic](src/reporting.py)
- [Declared policy](config/experiment_policy.json)
- [Guardrail tests](tests/test_experiment_guardrails.py)
- [Conversion-positive scenarios that block rollout](outputs/guardrail_scenarios.md)
