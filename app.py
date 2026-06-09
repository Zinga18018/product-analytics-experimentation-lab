from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.analytics import (
    ab_test_purchase_result,
    channel_performance,
    cohort_retention,
    connect,
    funnel_by_variant,
    table_counts,
)
from src.data_generator import GenerationConfig, build_database


ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "product_analytics.sqlite"

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
    if st.button("Rebuild dataset", use_container_width=True):
        counts = build_database(DB_PATH, GenerationConfig())
        st.success(f"Rebuilt dataset with {counts['users']:,} users.")

if not DB_PATH.exists():
    build_database(DB_PATH, GenerationConfig())

with connect(DB_PATH) as conn:
    counts = table_counts(conn)
    funnel = funnel_by_variant(conn)
    ab_result = ab_test_purchase_result(conn)
    channels = channel_performance(conn)
    retention = cohort_retention(conn)

metric_cols = st.columns(4)
metric_cols[0].metric("Users", f"{counts['users']:,}")
metric_cols[1].metric("Sessions", f"{counts['sessions']:,}")
metric_cols[2].metric("Events", f"{counts['events']:,}")
metric_cols[3].metric("Purchase lift", f"{ab_result['relative_lift_percent']:.2f}%")

st.subheader("Experiment Readout")
exp_cols = st.columns(4)
exp_cols[0].metric("Control rate", f"{ab_result['control_rate']:.2%}")
exp_cols[1].metric("Treatment rate", f"{ab_result['treatment_rate']:.2%}")
exp_cols[2].metric("p-value", ab_result["p_value"])
exp_cols[3].metric("Significant", "yes" if ab_result["statistically_significant_05"] else "no")

st.dataframe(funnel, hide_index=True, use_container_width=True)

st.subheader("Acquisition Channel Performance")
st.bar_chart(channels.set_index("acquisition_channel")["revenue_per_user"])
st.dataframe(channels, hide_index=True, use_container_width=True)

st.subheader("Cohort Retention")
retention_chart = retention.set_index("signup_week")[["retention_7d", "retention_14d", "retention_30d"]]
st.line_chart(retention_chart)
st.dataframe(retention, hide_index=True, use_container_width=True)

st.subheader("Interpretation")
if ab_result["statistically_significant_05"] and ab_result["absolute_lift"] > 0:
    st.success("Treatment shows statistically significant purchase-rate lift in the simulated experiment.")
elif ab_result["absolute_lift"] > 0:
    st.info("Treatment lift is positive, but the simulated evidence is not statistically strong enough yet.")
else:
    st.warning("Treatment did not improve purchase conversion in the simulated experiment.")

st.caption("All results are generated from synthetic data for portfolio/interview practice.")
