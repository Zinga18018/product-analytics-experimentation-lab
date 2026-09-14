from __future__ import annotations

import sqlite3

from src.analytics import DEFAULT_POLICY, ExperimentPolicy, channel_performance, cohort_retention, experiment_readout, table_counts


def format_number(value, percent=False) -> str:
    if value is None:
        return "unavailable"
    return f"{value:.2%}" if percent else f"{value:.4f}"


def build_markdown_report(conn: sqlite3.Connection, policy: ExperimentPolicy = DEFAULT_POLICY) -> str:
    readout = experiment_readout(conn, policy)
    conversion, retention, revenue = (readout[key] for key in ("conversion", "retention", "revenue"))
    lines = ["# Product Analytics Experimentation Report", "",
             "Synthetic data only. This is a fixed-horizon demonstration, not a measured business outcome.", "",
             "## Dataset", ""]
    lines += [f"- {name}: {count:,}" for name, count in table_counts(conn).items()]
    lines += ["", "## Declared analysis policy", "",
              "These are illustrative policy settings. In a real experiment, agree on them before inspecting outcomes.", "",
              f"- Experiment: `{policy.experiment_name}`; exclusive UTC cutoff: `{policy.as_of}`.",
              f"- Conversion and revenue windows: first {policy.conversion_days} and {policy.revenue_days} days after assignment, respectively.",
              f"- Retention: any session on days {policy.retention_start_day}-{policy.retention_end_day} after assignment.",
              f"- Require all {policy.horizon_days} follow-up days: {readout['eligible_users']:,} eligible users; {readout['excluded_immature_users']:,} enrolled users excluded as immature.",
              "- Denominator: all eligible assigned users, including users with no activity or purchases.",
              f"- Expected treatment allocation: {policy.expected_treatment_share:.0%}; SRM threshold: {policy.srm_alpha}.",
              f"- Minimum eligible users per arm: {policy.min_users_per_arm}; confidence level: {readout['confidence_level']:.0%}.",
              f"- Minimum conversion lift: {policy.min_conversion_lift:.2%}; allowed retention loss: {policy.retention_loss_tolerance * 100:.2f} percentage points; allowed revenue loss: {policy.revenue_loss_tolerance:.2f} currency units per assigned user.",
              "", "## Experiment readout", "",
              "All differences below are treatment minus control; intervals are two-sided.", "",
              "| Metric | Control | Treatment | Difference | Confidence interval |",
              "| --- | ---: | ---: | ---: | --- |"]
    for label, result in (("Purchase conversion", conversion), ("Retention", retention)):
        lines.append(f"| {label} | {format_number(result['control_rate'], True)} | {format_number(result['treatment_rate'], True)} | {format_number(result['absolute_lift'], True)} | [{format_number(result['ci_low'], True)}, {format_number(result['ci_high'], True)}] |")
    lines.append(f"| Revenue per assigned user | {format_number(revenue['control_mean'])} | {format_number(revenue['treatment_mean'])} | {format_number(revenue['difference'])} | [{format_number(revenue['ci_low'])}, {format_number(revenue['ci_high'])}] |")
    lines += ["", f"- Eligible control/treatment users: {conversion['control_users']:,}/{conversion['treatment_users']:,}.",
              f"- Purchase control/treatment users: {conversion['control_purchases']:,}/{conversion['treatment_purchases']:,}.",
              f"- Two-proportion conversion p-value: {format_number(conversion['p_value'])}.",
              f"- Relative conversion lift: {format_number(conversion['relative_lift_percent'])}% (undefined when control conversion is zero).",
              "- Binary difference intervals: Newcombe method using Wilson score bounds.",
              f"- Revenue uncertainty: {revenue['method']}.", "", "## Rollout gates", ""]
    for cohort, result in readout["sample_ratio"].items():
        lines.append(f"- {cohort.capitalize()} sample-ratio check: control={result['control_users']}, treatment={result['treatment_users']}, exact binomial p={format_number(result['p_value'])}.")
    lines += ["", "| Gate | Result |", "| --- | --- |"]
    lines += [f"| {name} | {'pass' if passed else 'blocked / unestablished'} |" for name, passed in readout["checks"].items()]
    lines += ["", f"**Decision: {readout['decision']}**", "", readout["recommendation"], "",
              "A guardrail passes only when its lower confidence bound is above the negative loss tolerance. A non-significant harm test does not establish safety. Failing a guardrail may mean harm or insufficient precision.", "",
              "## Acquisition channels (descriptive, all observed time)", "",
              "These channel rankings are not causal comparisons and do not use the experiment observation window.", "",
              _to_markdown_table(channel_performance(conn)), "", "## Signup-cohort retention", "",
              "Activity windows are days 1-7, 8-14, and 15-30. Each includes inactive users and only users with complete follow-up for that window. Unavailable windows are labeled unavailable, not zero.", "",
              _to_markdown_table(cohort_retention(conn, policy.as_of)), "", "## Limitations", "",
              "- Fixed-horizon, user-randomized, two-arm design only. No correction for repeated looks or exploratory segment testing.",
              "- Confidence intervals are marginal, not a simultaneous joint confidence region. All prespecified gates must pass; this is a conservative review rule, not automatic deployment.",
              "- Revenue intervals use Welch's approximation; heavy tails, refunds, incomplete event capture and novelty effects require further diagnostics in real data.",
              "- Minimum sample size is an illustrative floor, not a power calculation. Synthetic generator effects cannot establish real customer value.", ""]
    return "\n".join(lines)


def _to_markdown_table(frame) -> str:
    columns = [str(column) for column in frame.columns]
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame.fillna("unavailable").iterrows():
        rows.append("| " + " | ".join(str(row[column]) for column in frame.columns) + " |")
    return "\n".join(rows)
