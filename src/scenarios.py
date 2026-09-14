"""Deterministic stress scenarios with deliberately constructed effects, not measured results."""
from __future__ import annotations

import sqlite3


def scenario_database(*, control_users=500, treatment_users=500,
                      control_conversion=.2, treatment_conversion=.5,
                      control_retention=.3, treatment_retention=.7,
                      control_order_value=100.0, treatment_order_value=100.0) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
      CREATE TABLE users(user_id INTEGER, signup_date TEXT, acquisition_channel TEXT);
      CREATE TABLE experiment_assignments(user_id INTEGER, experiment_name TEXT, variant TEXT, assigned_at TEXT);
      CREATE TABLE events(event_id INTEGER, user_id INTEGER, event_name TEXT, event_time TEXT, revenue REAL);
      CREATE TABLE sessions(session_id INTEGER, user_id INTEGER, session_started_at TEXT);
      CREATE INDEX events_user ON events(user_id);
      CREATE INDEX sessions_user ON sessions(user_id);
    """)
    uid = 0
    for variant, n, conversion, retention, order in (
        ("control", control_users, control_conversion, control_retention, control_order_value),
        ("treatment", treatment_users, treatment_conversion, treatment_retention, treatment_order_value),
    ):
        for i in range(n):
            uid += 1
            conn.execute("INSERT INTO users VALUES (?, '2026-01-01', 'synthetic')", (uid,))
            conn.execute("INSERT INTO experiment_assignments VALUES (?, 'onboarding_redesign', ?, '2026-01-01T00:00:00')", (uid, variant))
            if i < round(n * conversion):
                conn.execute("INSERT INTO events VALUES (?, ?, 'purchase', '2026-01-01T12:00:00', ?)", (uid, uid, order))
            if i < round(n * retention):
                conn.execute("INSERT INTO sessions VALUES (?, ?, '2026-01-03T12:00:00')", (uid, uid))
    conn.commit()
    return conn


SCENARIOS = {
    "conversion_gain_retention_loss": {"control_retention": .7, "treatment_retention": .3},
    "conversion_gain_revenue_loss": {"treatment_order_value": 2.0},
    "conversion_gain_assignment_mismatch": {"treatment_users": 1000},
    "all_gates_pass": {},
}
