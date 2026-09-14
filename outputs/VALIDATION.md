# Local verification — September 14, 2026

This records local synthetic verification. It does not assert cloud deployment or real customer impact.

## Environment

- Python 3.14.7, pandas 3.0.5, SciPy 1.18.1, Streamlit 1.63.0.
- Windows Application Control blocked the uv-created Python 3.12 launcher. A native signed-Python virtual environment worked: `C:/Python314/python.exe -m venv .venv314`.
- Dependencies installed into that local environment; `.venv*` and `.uv-cache` are ignored.

## Commands and results

| Check | Result |
| --- | --- |
| `python -m unittest discover tests -v` | 24 tests passed; final suite run 2.235 seconds |
| `python scripts/build_dataset.py` | 5,000 users; 5,000 assignments; 22,287 sessions; 64,908 events |
| `python scripts/run_analysis.py` | Markdown report and full-precision JSON readout written |
| `python scripts/run_guardrail_scenarios.py` | Four constructed scenarios completed; three hold and one eligible for review |
| `streamlit.testing.v1.AppTest.from_file('app.py').run(timeout=40)` | 0 exceptions; 8 metrics; displayed retention-blocked hold recommendation |
| Three parameter-bound examples in `sql/product_metrics.sql` | Executed successfully: 2 variant rows, 5 channel rows, 9 cohort rows |

The Streamlit test exercises the app execution and rendered element tree, not a browser screenshot or deployed website. Streamlit emitted deprecation warnings for pre-existing `use_container_width` arguments.

## Main generated result

The declared March 2, 2026 exclusive cutoff gives **4,413 eligible users** (2,179 control and 2,234 treatment), with **587 immature assignments excluded**. The first-seven-day purchase counts are 384 and 474.

- Conversion difference: +3.59 percentage points; 95% interval [1.26, 5.92] percentage points.
- Retention difference: -0.61 percentage points; 95% interval [-3.49, 2.26] percentage points.
- Revenue difference: +4.3875 currency units per assigned user; 95% interval [1.0814, 7.6936].
- Decision: **hold**. Retention's lower bound does not clear the declared -2 percentage-point tolerance, despite the conversion gain.

The policy values are illustrative and were introduced as part of this implementation; they were not prospectively preregistered before the historical synthetic data were generated. A real study needs an agreed analysis plan and power calculation before exposure or outcome inspection.

## Coverage and limits

Tests cover harmful retention, harmful revenue, assignment mismatch, all gates passing, inconclusive retention, inactive-user denominators, follow-up and event-time boundaries, unrelated experiments, duplicate assignments/events, invalid timestamps, missing revenue, empty/missing arms, zero conversion and revenue variance, small samples and policy validation. Wilson intervals are compared with SciPy's implementation; revenue intervals with SciPy's Welch result.

These tests establish implementation behavior on constructed data. They do not validate causal assumptions, real-world loss tolerances, revenue-tail robustness, sequential testing, or external product benefit.
