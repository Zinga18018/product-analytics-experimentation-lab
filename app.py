from __future__ import annotations

from pathlib import Path
import json

import pandas as pd
import streamlit as st

from src.analytics import (
    ExperimentPolicy,
    experiment_readout,
    channel_performance,
    cohort_retention,
    connect,
    funnel_by_variant,
    table_counts,
)
from src.data_generator import GenerationConfig, build_database
from src.reporting import format_number


ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "product_analytics.sqlite"
POLICY = ExperimentPolicy(**json.loads((ROOT / "config" / "experiment_policy.json").read_text(encoding="utf-8")))

st.set_page_config(
    page_title="Product Analytics Experimentation Lab",
    page_icon="PA",
    layout="wide",
)

st.title("Product Analytics Experimentation Lab")
st.caption("SQL-backed product metrics, cohort retention, and A/B testing.")

with st.sidebar:
    st.header("Dataset")
    st.write("Synthetic, deterministic product-event data.")
    st.caption(f"Exclusive observation cutoff: {POLICY.as_of}. Policy settings are illustrative and must be agreed before real analysis.")
    if st.button("Rebuild dataset", use_container_width=True):
        counts = build_database(DB_PATH, GenerationConfig())
        st.success(f"Rebuilt dataset with {counts['users']:,} users.")

if not DB_PATH.exists():
    build_database(DB_PATH, GenerationConfig())

with connect(DB_PATH) as conn:
    counts = table_counts(conn)
    funnel = funnel_by_variant(conn, POLICY)
    readout = experiment_readout(conn, POLICY)
    ab_result = readout["conversion"]
    channels = channel_performance(conn)
    retention = cohort_retention(conn, POLICY.as_of)

metric_cols = st.columns(4)
metric_cols[0].metric("Users", f"{counts['users']:,}")
metric_cols[1].metric("Sessions", f"{counts['sessions']:,}")
metric_cols[2].metric("Events", f"{counts['events']:,}")
metric_cols[3].metric("Eligible users", f"{readout['eligible_users']:,}")

st.subheader("Experiment Readout")
exp_cols = st.columns(4)
exp_cols[0].metric("Control rate", format_number(ab_result["control_rate"], True))
exp_cols[1].metric("Treatment rate", format_number(ab_result["treatment_rate"], True))
exp_cols[2].metric("Conversion p-value", format_number(ab_result["p_value"]))
exp_cols[3].metric("Decision", readout["decision"])
st.caption(f"All assigned users with {POLICY.horizon_days} complete follow-up days are included, even without activity. {readout['excluded_immature_users']} recent assignments are not yet eligible.")
st.write(f"{readout['confidence_level']:.0%} conversion difference interval: {format_number(ab_result['ci_low'], True)} to {format_number(ab_result['ci_high'], True)}.")

st.dataframe(funnel, hide_index=True, use_container_width=True)
st.subheader("Rollout guardrails")
st.dataframe(pd.DataFrame([{"gate": name, "passed": passed} for name, passed in readout["checks"].items()]), hide_index=True)
st.write(f"Retention loss tolerance: {POLICY.retention_loss_tolerance * 100:.2f} percentage points. Revenue loss tolerance: {POLICY.revenue_loss_tolerance:.2f} currency units per assigned user.")
st.write(f"Retention difference interval: {format_number(readout['retention']['ci_low'], True)} to {format_number(readout['retention']['ci_high'], True)}.")
st.write(f"Revenue difference interval: {format_number(readout['revenue']['ci_low'])} to {format_number(readout['revenue']['ci_high'])}.")
with st.expander("Declared policy and assignment checks"):
    st.json({"policy": readout["policy"], "sample_ratio": readout["sample_ratio"]})

st.subheader("Acquisition Channel Performance")
st.caption("Descriptive all-observed-time metrics; these do not determine the experiment decision.")
st.bar_chart(channels.set_index("acquisition_channel")["revenue_per_user"])
st.dataframe(channels, hide_index=True, use_container_width=True)

st.subheader("Cohort Retention")
st.caption("Activity windows: days 1-7, 8-14, 15-30. Each denominator includes inactive users with full observation for that window. Unavailable windows are not zeros.")
retention_chart = retention.set_index("signup_week")[["retention_7d", "retention_14d", "retention_30d"]]
st.line_chart(retention_chart)
st.dataframe(retention, hide_index=True, use_container_width=True)

st.subheader("Interpretation")
if readout["decision"] == "eligible_for_rollout_review":
    st.success(readout["recommendation"])
else:
    st.warning(readout["recommendation"])

st.caption("All results are generated from synthetic data for portfolio/interview practice.")
