from __future__ import annotations

import math
import sqlite3
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from statistics import NormalDist

import pandas as pd
from scipy.stats import binomtest, t


@dataclass(frozen=True)
class ExperimentPolicy:
    """Illustrative, pre-analysis policy for the synthetic experiment, not business policy."""

    experiment_name: str = "onboarding_redesign"
    as_of: str = "2026-03-02"  # Exclusive UTC cutoff; matches the default synthetic dataset.
    conversion_days: int = 7
    retention_start_day: int = 1
    retention_end_day: int = 7
    revenue_days: int = 7
    expected_treatment_share: float = 0.5
    alpha: float = 0.05
    srm_alpha: float = 0.001
    min_users_per_arm: int = 100
    min_conversion_lift: float = 0.0
    retention_loss_tolerance: float = 0.02  # Absolute fraction: 2 percentage points.
    revenue_loss_tolerance: float = 1.0  # Synthetic currency units per assigned user.

    def __post_init__(self) -> None:
        date.fromisoformat(self.as_of)
        if not self.experiment_name:
            raise ValueError("experiment_name must be supplied")
        for name in ("conversion_days", "revenue_days", "retention_start_day", "retention_end_day"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.retention_end_day < self.retention_start_day:
            raise ValueError("retention_end_day must be at least retention_start_day")
        if type(self.min_users_per_arm) is not int or self.min_users_per_arm < 2:
            raise ValueError("min_users_per_arm must be at least 2")
        for name in ("expected_treatment_share", "alpha", "srm_alpha"):
            if not 0 < getattr(self, name) < 1:
                raise ValueError(f"{name} must be between 0 and 1")
        for name in ("min_conversion_lift", "retention_loss_tolerance", "revenue_loss_tolerance"):
            if not math.isfinite(getattr(self, name)) or getattr(self, name) < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if self.min_conversion_lift > 1 or self.retention_loss_tolerance > 1:
            raise ValueError("Proportion tolerances must not exceed 1")

    @property
    def horizon_days(self) -> int:
        return max(self.conversion_days, self.revenue_days, self.retention_end_day + 1)


DEFAULT_POLICY = ExperimentPolicy()


def connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    return sqlite3.connect(db_path)


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("users", "experiment_assignments", "sessions", "events")}


def _validate_assignments(conn: sqlite3.Connection, policy: ExperimentPolicy) -> None:
    assignments = pd.read_sql_query(
        "SELECT * FROM experiment_assignments WHERE experiment_name = ?", conn,
        params=(policy.experiment_name,),
    )
    if assignments.user_id.isna().any() or assignments.user_id.duplicated().any():
        raise ValueError("Selected experiment must have exactly one assignment per user")
    if not assignments.variant.isin(["control", "treatment"]).all():
        raise ValueError("Selected experiment has missing or unsupported variants")
    invalid_assignment_times = conn.execute("""
        SELECT COUNT(*) FROM experiment_assignments
        WHERE experiment_name = ? AND JULIANDAY(assigned_at) IS NULL
    """, (policy.experiment_name,)).fetchone()[0]
    if invalid_assignment_times:
        raise ValueError("Selected experiment has invalid assignment timestamps")
    bad_users = conn.execute("""
        SELECT COUNT(*) FROM experiment_assignments a
        WHERE a.experiment_name = ? AND
          (SELECT COUNT(*) FROM users u WHERE u.user_id = a.user_id) <> 1
    """, (policy.experiment_name,)).fetchone()[0]
    if bad_users:
        raise ValueError("Each assigned user must have exactly one users row")
    for table, timestamp in (("events", "event_time"), ("sessions", "session_started_at")):
        bad_times = conn.execute(f"""
            SELECT COUNT(*) FROM {table} x JOIN experiment_assignments a USING(user_id)
            WHERE a.experiment_name = ? AND JULIANDAY(x.{timestamp}) IS NULL
        """, (policy.experiment_name,)).fetchone()[0]
        if bad_times:
            raise ValueError(f"Invalid {table} timestamps would silently change metric eligibility")
    revenues = pd.read_sql_query("""
        SELECT e.revenue FROM events e JOIN experiment_assignments a USING(user_id)
        WHERE a.experiment_name = ? AND e.event_name = 'purchase'
          AND JULIANDAY(e.event_time) >= JULIANDAY(a.assigned_at)
          AND JULIANDAY(e.event_time) < JULIANDAY(?)
    """, conn, params=(policy.experiment_name, policy.as_of)).revenue
    if any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in revenues):
        raise ValueError("Purchase revenue must be finite numeric data; missing revenue is not zero")
    duplicate_events = conn.execute("""
        SELECT COUNT(*) FROM (
          SELECT e.event_id FROM events e JOIN experiment_assignments a USING(user_id)
          WHERE a.experiment_name = ? GROUP BY e.event_id HAVING COUNT(*) > 1
        )
    """, (policy.experiment_name,)).fetchone()[0]
    if duplicate_events:
        raise ValueError("Duplicate event IDs would inflate revenue")


def experiment_user_metrics(conn: sqlite3.Connection, policy: ExperimentPolicy = DEFAULT_POLICY) -> pd.DataFrame:
    """One row per mature assigned user, including users without any activity."""
    _validate_assignments(conn, policy)
    return pd.read_sql_query("""
        WITH eligible AS (
            SELECT user_id, variant, assigned_at FROM experiment_assignments
            WHERE experiment_name = :experiment_name
              AND JULIANDAY(assigned_at) + :horizon_days <= JULIANDAY(:as_of)
        )
        SELECT a.user_id, a.variant,
            MAX(CASE WHEN e.event_name = 'view_landing'
                AND JULIANDAY(e.event_time) < JULIANDAY(a.assigned_at) + :conversion_days THEN 1 ELSE 0 END) AS viewed_landing,
            MAX(CASE WHEN e.event_name = 'view_product'
                AND JULIANDAY(e.event_time) < JULIANDAY(a.assigned_at) + :conversion_days THEN 1 ELSE 0 END) AS viewed_product,
            MAX(CASE WHEN e.event_name = 'start_checkout'
                AND JULIANDAY(e.event_time) < JULIANDAY(a.assigned_at) + :conversion_days THEN 1 ELSE 0 END) AS started_checkout,
            MAX(CASE WHEN e.event_name = 'purchase'
                AND JULIANDAY(e.event_time) < JULIANDAY(a.assigned_at) + :conversion_days THEN 1 ELSE 0 END) AS purchased,
            SUM(CASE WHEN e.event_name = 'purchase'
                AND JULIANDAY(e.event_time) < JULIANDAY(a.assigned_at) + :revenue_days THEN e.revenue ELSE 0.0 END) AS revenue,
            EXISTS(SELECT 1 FROM sessions s WHERE s.user_id = a.user_id
                AND JULIANDAY(s.session_started_at) >= JULIANDAY(a.assigned_at) + :retention_start_day
                AND JULIANDAY(s.session_started_at) < JULIANDAY(a.assigned_at) + :retention_end_day + 1) AS retained
        FROM eligible a LEFT JOIN events e ON a.user_id = e.user_id
            AND JULIANDAY(e.event_time) >= JULIANDAY(a.assigned_at)
            AND JULIANDAY(e.event_time) < JULIANDAY(a.assigned_at) + :horizon_days
        GROUP BY a.user_id, a.variant, a.assigned_at ORDER BY a.user_id
    """, conn, params={**asdict(policy), "horizon_days": policy.horizon_days})


def funnel_by_variant(conn: sqlite3.Connection, policy: ExperimentPolicy = DEFAULT_POLICY) -> pd.DataFrame:
    metrics = experiment_user_metrics(conn, policy)
    rows = []
    for variant in ("control", "treatment"):
        arm = metrics[metrics.variant == variant]
        n = len(arm)
        rows.append({"variant": variant, "assigned_users": n,
                     "viewed_landing_users": int(arm.viewed_landing.sum()),
                     "viewed_product_users": int(arm.viewed_product.sum()),
                     "checkout_users": int(arm.started_checkout.sum()),
                     "purchase_users": int(arm.purchased.sum()),
                     "checkout_rate": float(arm.started_checkout.mean()) if n else None,
                     "purchase_rate": float(arm.purchased.mean()) if n else None})
    return pd.DataFrame(rows)


def _wilson(successes: int, n: int, alpha: float) -> tuple[float, float]:
    z = NormalDist().inv_cdf(1 - alpha / 2)
    rate = successes / n
    denominator = 1 + z * z / n
    midpoint = (rate + z * z / (2 * n)) / denominator
    half_width = z * math.sqrt(rate * (1 - rate) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, midpoint - half_width), min(1.0, midpoint + half_width)


def _binary_result(control: pd.Series, treatment: pd.Series, alpha: float) -> dict:
    nc, nt = len(control), len(treatment)
    result = {"control_users": nc, "treatment_users": nt,
              "control_successes": int(control.sum()), "treatment_successes": int(treatment.sum()),
              "control_rate": None, "treatment_rate": None, "absolute_lift": None,
              "ci_low": None, "ci_high": None, "p_value": None, "z_score": None,
              "normal_test_eligible": False}
    if not nc or not nt:
        return result
    xc, xt = result["control_successes"], result["treatment_successes"]
    pc, pt = xc / nc, xt / nt
    lc, uc = _wilson(xc, nc, alpha)
    lt, ut = _wilson(xt, nt, alpha)
    delta = pt - pc
    # Newcombe independent-proportion difference interval from Wilson bounds.
    result.update(control_rate=pc, treatment_rate=pt, absolute_lift=delta,
                  ci_low=delta - math.sqrt((pt - lt) ** 2 + (uc - pc) ** 2),
                  ci_high=delta + math.sqrt((ut - pt) ** 2 + (pc - lc) ** 2))
    # Do not report a large-sample p-value for degenerate/sparse counts.
    if min(xc, xt, nc - xc, nt - xt) >= 5:
        pooled = (xc + xt) / (nc + nt)
        se = math.sqrt(pooled * (1 - pooled) * (1 / nc + 1 / nt))
        z = delta / se
        result.update(z_score=z, p_value=math.erfc(abs(z) / math.sqrt(2)), normal_test_eligible=True)
    return result


def _revenue_result(control: pd.Series, treatment: pd.Series, alpha: float) -> dict:
    result = {"control_mean": None, "treatment_mean": None, "difference": None,
              "ci_low": None, "ci_high": None, "method": "Welch t interval on revenue per assigned user"}
    if len(control) < 2 or len(treatment) < 2:
        return result
    mc, mt = float(control.mean()), float(treatment.mean())
    vc, vt = float(control.var(ddof=1)) / len(control), float(treatment.var(ddof=1)) / len(treatment)
    result.update(control_mean=mc, treatment_mean=mt, difference=mt - mc)
    if vc + vt == 0:
        result["method"] += "; unavailable because both sample variances are zero"
        return result
    df = (vc + vt) ** 2 / (vc * vc / (len(control) - 1) + vt * vt / (len(treatment) - 1))
    half = float(t.ppf(1 - alpha / 2, df)) * math.sqrt(vc + vt)
    result.update(ci_low=mt - mc - half, ci_high=mt - mc + half)
    return result


def experiment_readout(conn: sqlite3.Connection, policy: ExperimentPolicy = DEFAULT_POLICY) -> dict:
    metrics = experiment_user_metrics(conn, policy)
    c, tr = (metrics[metrics.variant == variant] for variant in ("control", "treatment"))
    conversion = _binary_result(c.purchased, tr.purchased, policy.alpha)
    conversion.update(control_purchases=conversion["control_successes"],
                      treatment_purchases=conversion["treatment_successes"])
    conversion["relative_lift_percent"] = (
        100 * conversion["absolute_lift"] / conversion["control_rate"]
        if conversion["control_rate"] else None)
    conversion["statistically_significant_05"] = conversion["p_value"] is not None and conversion["p_value"] < .05
    retention = _binary_result(c.retained, tr.retained, policy.alpha)
    revenue = _revenue_result(c.revenue, tr.revenue, policy.alpha)
    assigned = pd.read_sql_query("""
        SELECT variant, COUNT(*) n FROM experiment_assignments
        WHERE experiment_name = ? AND JULIANDAY(assigned_at) < JULIANDAY(?) GROUP BY variant
    """, conn, params=(policy.experiment_name, policy.as_of)).set_index("variant").n.to_dict()
    srm = {}
    for name, nc, nt in (("enrolled", int(assigned.get("control", 0)), int(assigned.get("treatment", 0))),
                         ("eligible", len(c), len(tr))):
        p = float(binomtest(nt, nc + nt, policy.expected_treatment_share).pvalue) if nc + nt else None
        srm[name] = {"control_users": nc, "treatment_users": nt, "p_value": p,
                     "passed": p is not None and p >= policy.srm_alpha}
    checks = {
        "minimum_sample": len(c) >= policy.min_users_per_arm and len(tr) >= policy.min_users_per_arm,
        "sample_ratio": all(value["passed"] for value in srm.values()),
        "conversion": (conversion["normal_test_eligible"] and conversion["p_value"] < policy.alpha
                       and conversion["ci_low"] > policy.min_conversion_lift),
        "retention": retention["ci_low"] is not None and retention["ci_low"] > -policy.retention_loss_tolerance,
        "revenue": revenue["ci_low"] is not None and revenue["ci_low"] > -policy.revenue_loss_tolerance,
    }
    reasons = {
        "minimum_sample": "Insufficient fully observed users in at least one arm.",
        "sample_ratio": "Assignment or eligible-cohort sample ratio failed or could not be assessed.",
        "conversion": "Conversion improvement is not established above the declared minimum lift.",
        "retention": "Retention noninferiority is not established within the declared loss tolerance.",
        "revenue": "Revenue noninferiority is not established within the declared loss tolerance.",
    }
    blockers = [reasons[name] for name, passed in checks.items() if not passed]
    return {"policy": asdict(policy), "confidence_level": 1 - policy.alpha,
            "eligible_users": len(metrics), "excluded_immature_users": sum(assigned.values()) - len(metrics),
            "conversion": conversion, "retention": retention, "revenue": revenue,
            "sample_ratio": srm, "checks": checks, "blockers": blockers,
            "decision": "eligible_for_rollout_review" if not blockers else "hold",
            "recommendation": ("Eligible for a staged rollout review under the declared synthetic policy."
                               if not blockers else "Hold rollout. " + " ".join(blockers))}


def ab_test_purchase_result(conn: sqlite3.Connection, policy: ExperimentPolicy = DEFAULT_POLICY) -> dict:
    return experiment_readout(conn, policy)["conversion"]


def channel_performance(conn: sqlite3.Connection) -> pd.DataFrame:
    """Descriptive all-observed-time channel metrics, not experiment decision evidence."""
    return pd.read_sql_query("""
        SELECT u.acquisition_channel, COUNT(DISTINCT u.user_id) AS users,
          COUNT(DISTINCT CASE WHEN e.event_name = 'purchase' THEN u.user_id END) AS purchasers,
          1.0 * COUNT(DISTINCT CASE WHEN e.event_name = 'purchase' THEN u.user_id END)
              / COUNT(DISTINCT u.user_id) AS purchase_rate,
          ROUND(COALESCE(SUM(CASE WHEN e.event_name = 'purchase' THEN e.revenue ELSE 0 END), 0), 2) AS revenue,
          ROUND(COALESCE(SUM(CASE WHEN e.event_name = 'purchase' THEN e.revenue ELSE 0 END), 0)
              / COUNT(DISTINCT u.user_id), 2) AS revenue_per_user
        FROM users u LEFT JOIN events e ON u.user_id = e.user_id
        GROUP BY u.acquisition_channel ORDER BY revenue_per_user DESC
    """, conn)


def cohort_retention(conn: sqlite3.Connection, as_of: str = DEFAULT_POLICY.as_of) -> pd.DataFrame:
    """Signup-week window activity; each window has its own fully observed denominator."""
    date.fromisoformat(as_of)
    return pd.read_sql_query("""
        WITH user_windows AS (
          SELECT u.user_id, STRFTIME('%Y-%W', u.signup_date) signup_week,
            JULIANDAY(u.signup_date) + 8 <= JULIANDAY(:as_of) eligible_7d,
            JULIANDAY(u.signup_date) + 15 <= JULIANDAY(:as_of) eligible_14d,
            JULIANDAY(u.signup_date) + 31 <= JULIANDAY(:as_of) eligible_30d,
            MAX(CASE WHEN JULIANDAY(s.session_started_at) >= JULIANDAY(u.signup_date) + 1
                AND JULIANDAY(s.session_started_at) < JULIANDAY(u.signup_date) + 8 THEN 1 ELSE 0 END) r7,
            MAX(CASE WHEN JULIANDAY(s.session_started_at) >= JULIANDAY(u.signup_date) + 8
                AND JULIANDAY(s.session_started_at) < JULIANDAY(u.signup_date) + 15 THEN 1 ELSE 0 END) r14,
            MAX(CASE WHEN JULIANDAY(s.session_started_at) >= JULIANDAY(u.signup_date) + 15
                AND JULIANDAY(s.session_started_at) < JULIANDAY(u.signup_date) + 31 THEN 1 ELSE 0 END) r30
          FROM users u LEFT JOIN sessions s ON u.user_id = s.user_id
              AND JULIANDAY(s.session_started_at) < JULIANDAY(:as_of)
          WHERE JULIANDAY(u.signup_date) < JULIANDAY(:as_of)
          GROUP BY u.user_id, u.signup_date
        )
        SELECT signup_week, COUNT(*) cohort_users,
          SUM(eligible_7d) eligible_7d_users, SUM(r7 * eligible_7d) retained_7d_users,
          1.0 * SUM(r7 * eligible_7d) / NULLIF(SUM(eligible_7d), 0) retention_7d,
          SUM(eligible_14d) eligible_14d_users, SUM(r14 * eligible_14d) retained_14d_users,
          1.0 * SUM(r14 * eligible_14d) / NULLIF(SUM(eligible_14d), 0) retention_14d,
          SUM(eligible_30d) eligible_30d_users, SUM(r30 * eligible_30d) retained_30d_users,
          1.0 * SUM(r30 * eligible_30d) / NULLIF(SUM(eligible_30d), 0) retention_30d
        FROM user_windows GROUP BY signup_week ORDER BY signup_week
    """, conn, params={"as_of": as_of})


def executive_summary(conn: sqlite3.Connection, policy: ExperimentPolicy = DEFAULT_POLICY) -> dict:
    readout = experiment_readout(conn, policy)
    channels = channel_performance(conn)
    return {"counts": table_counts(conn), "ab_test": readout["conversion"], "experiment": readout,
            "best_channel": channels.iloc[0].to_dict() if not channels.empty else None,
            "recommendation": readout["recommendation"]}
