from __future__ import annotations

import math
import sqlite3
from pathlib import Path

import pandas as pd


FUNNEL_EVENTS = ["view_landing", "view_product", "start_checkout", "purchase"]


def connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    return sqlite3.connect(db_path)


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = ["users", "experiment_assignments", "sessions", "events"]
    return {
        table: int(pd.read_sql_query(f"SELECT COUNT(*) AS n FROM {table}", conn).iloc[0]["n"])
        for table in tables
    }


def funnel_by_variant(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
    WITH user_events AS (
        SELECT
            ea.variant,
            ea.user_id,
            MAX(CASE WHEN e.event_name = 'view_landing' THEN 1 ELSE 0 END) AS viewed_landing,
            MAX(CASE WHEN e.event_name = 'view_product' THEN 1 ELSE 0 END) AS viewed_product,
            MAX(CASE WHEN e.event_name = 'start_checkout' THEN 1 ELSE 0 END) AS started_checkout,
            MAX(CASE WHEN e.event_name = 'purchase' THEN 1 ELSE 0 END) AS purchased
        FROM experiment_assignments ea
        LEFT JOIN events e
            ON ea.user_id = e.user_id
        GROUP BY ea.variant, ea.user_id
    )
    SELECT
        variant,
        COUNT(*) AS assigned_users,
        SUM(viewed_landing) AS viewed_landing_users,
        SUM(viewed_product) AS viewed_product_users,
        SUM(started_checkout) AS checkout_users,
        SUM(purchased) AS purchase_users,
        ROUND(1.0 * SUM(started_checkout) / COUNT(*), 4) AS checkout_rate,
        ROUND(1.0 * SUM(purchased) / COUNT(*), 4) AS purchase_rate
    FROM user_events
    GROUP BY variant
    ORDER BY variant;
    """
    return pd.read_sql_query(query, conn)


def ab_test_purchase_result(conn: sqlite3.Connection) -> dict:
    funnel = funnel_by_variant(conn).set_index("variant")
    control = funnel.loc["control"]
    treatment = funnel.loc["treatment"]

    control_n = int(control["assigned_users"])
    treatment_n = int(treatment["assigned_users"])
    control_x = int(control["purchase_users"])
    treatment_x = int(treatment["purchase_users"])
    control_rate = control_x / control_n
    treatment_rate = treatment_x / treatment_n
    lift = treatment_rate - control_rate
    relative_lift = lift / control_rate if control_rate else 0

    pooled = (control_x + treatment_x) / (control_n + treatment_n)
    standard_error = math.sqrt(pooled * (1 - pooled) * ((1 / control_n) + (1 / treatment_n)))
    z_score = lift / standard_error if standard_error else 0
    p_value = math.erfc(abs(z_score) / math.sqrt(2))

    return {
        "control_users": control_n,
        "treatment_users": treatment_n,
        "control_purchases": control_x,
        "treatment_purchases": treatment_x,
        "control_rate": round(control_rate, 4),
        "treatment_rate": round(treatment_rate, 4),
        "absolute_lift": round(lift, 4),
        "relative_lift_percent": round(relative_lift * 100, 2),
        "z_score": round(z_score, 4),
        "p_value": round(p_value, 6),
        "statistically_significant_05": p_value < 0.05,
    }


def channel_performance(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
    SELECT
        u.acquisition_channel,
        COUNT(DISTINCT u.user_id) AS users,
        COUNT(DISTINCT CASE WHEN e.event_name = 'purchase' THEN u.user_id END) AS purchasers,
        ROUND(1.0 * COUNT(DISTINCT CASE WHEN e.event_name = 'purchase' THEN u.user_id END)
              / COUNT(DISTINCT u.user_id), 4) AS purchase_rate,
        ROUND(SUM(e.revenue), 2) AS revenue,
        ROUND(SUM(e.revenue) / COUNT(DISTINCT u.user_id), 2) AS revenue_per_user
    FROM users u
    LEFT JOIN events e
        ON u.user_id = e.user_id
    GROUP BY u.acquisition_channel
    ORDER BY revenue_per_user DESC;
    """
    return pd.read_sql_query(query, conn)


def cohort_retention(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
    WITH first_seen AS (
        SELECT
            user_id,
            DATE(signup_date) AS signup_date,
            STRFTIME('%Y-%W', signup_date) AS signup_week
        FROM users
    ),
    activity AS (
        SELECT DISTINCT
            fs.user_id,
            fs.signup_week,
            CAST(JULIANDAY(s.session_date) - JULIANDAY(fs.signup_date) AS INTEGER) AS days_after_signup
        FROM first_seen fs
        JOIN sessions s
            ON fs.user_id = s.user_id
    )
    SELECT
        signup_week,
        COUNT(DISTINCT user_id) AS cohort_users,
        ROUND(1.0 * COUNT(DISTINCT CASE WHEN days_after_signup BETWEEN 1 AND 7 THEN user_id END)
              / COUNT(DISTINCT user_id), 4) AS retention_7d,
        ROUND(1.0 * COUNT(DISTINCT CASE WHEN days_after_signup BETWEEN 8 AND 14 THEN user_id END)
              / COUNT(DISTINCT user_id), 4) AS retention_14d,
        ROUND(1.0 * COUNT(DISTINCT CASE WHEN days_after_signup BETWEEN 15 AND 30 THEN user_id END)
              / COUNT(DISTINCT user_id), 4) AS retention_30d
    FROM activity
    GROUP BY signup_week
    ORDER BY signup_week;
    """
    return pd.read_sql_query(query, conn)


def executive_summary(conn: sqlite3.Connection) -> dict:
    counts = table_counts(conn)
    ab_result = ab_test_purchase_result(conn)
    channels = channel_performance(conn)
    best_channel = channels.iloc[0].to_dict()
    return {
        "counts": counts,
        "ab_test": ab_result,
        "best_channel": best_channel,
        "recommendation": _recommendation(ab_result),
    }


def _recommendation(ab_result: dict) -> str:
    if ab_result["statistically_significant_05"] and ab_result["absolute_lift"] > 0:
        return "Ship treatment to a larger rollout while monitoring retention and revenue per user."
    if ab_result["absolute_lift"] > 0:
        return "Keep the experiment running longer; observed lift is positive but not yet statistically strong."
    return "Do not ship treatment; investigate friction before another experiment."
