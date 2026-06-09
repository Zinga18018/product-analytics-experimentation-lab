from __future__ import annotations

import sqlite3

from src.analytics import ab_test_purchase_result, channel_performance, cohort_retention, table_counts


def build_markdown_report(conn: sqlite3.Connection) -> str:
    counts = table_counts(conn)
    ab_result = ab_test_purchase_result(conn)
    channels = channel_performance(conn)
    retention = cohort_retention(conn)

    lines = [
        "# Product Analytics Experimentation Report",
        "",
        "## Dataset",
        "",
        f"- Users: {counts['users']:,}",
        f"- Experiment assignments: {counts['experiment_assignments']:,}",
        f"- Sessions: {counts['sessions']:,}",
        f"- Events: {counts['events']:,}",
        "",
        "## Experiment Readout",
        "",
        f"- Control purchase rate: {ab_result['control_rate']:.2%}",
        f"- Treatment purchase rate: {ab_result['treatment_rate']:.2%}",
        f"- Absolute lift: {ab_result['absolute_lift']:.2%}",
        f"- Relative lift: {ab_result['relative_lift_percent']:.2f}%",
        f"- z-score: {ab_result['z_score']}",
        f"- p-value: {ab_result['p_value']}",
        f"- Significant at 0.05: {ab_result['statistically_significant_05']}",
        "",
        "## Recommendation",
        "",
    ]

    if ab_result["statistically_significant_05"] and ab_result["absolute_lift"] > 0:
        lines.append("Ship the onboarding redesign to a larger rollout while monitoring retention and revenue per user.")
    elif ab_result["absolute_lift"] > 0:
        lines.append("Continue the experiment because observed lift is positive but not statistically strong enough yet.")
    else:
        lines.append("Do not ship the treatment; investigate onboarding friction and retest.")

    lines.extend(
        [
            "",
            "## Top Acquisition Channels",
            "",
            _to_markdown_table(channels.head(5)),
            "",
            "## Cohort Retention Sample",
            "",
            _to_markdown_table(retention.head(8)),
            "",
        ]
    )
    return "\n".join(lines)


def _to_markdown_table(frame) -> str:
    columns = [str(column) for column in frame.columns]
    rows = []
    rows.append("| " + " | ".join(columns) + " |")
    rows.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for _, row in frame.iterrows():
        values = [str(row[column]) for column in frame.columns]
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)
