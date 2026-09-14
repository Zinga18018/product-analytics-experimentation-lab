from __future__ import annotations

from dataclasses import replace
import math
import unittest

import pandas as pd
from scipy.stats import binomtest, ttest_ind

from src.analytics import DEFAULT_POLICY, ExperimentPolicy, _binary_result, _wilson, cohort_retention, experiment_readout, experiment_user_metrics
from src.reporting import build_markdown_report
from src.scenarios import scenario_database


class ExperimentGuardrailTests(unittest.TestCase):
    def scenario(self, **kwargs):
        conn = scenario_database(**kwargs)
        self.addCleanup(conn.close)
        return conn

    def test_positive_conversion_is_blocked_by_retention(self):
        result = experiment_readout(self.scenario(control_retention=.7, treatment_retention=.3))
        self.assertTrue(result["checks"]["conversion"])
        self.assertTrue(result["checks"]["revenue"])
        self.assertFalse(result["checks"]["retention"])
        self.assertLess(result["retention"]["ci_high"], -.02)
        self.assertEqual(result["decision"], "hold")

    def test_positive_conversion_is_blocked_by_revenue(self):
        result = experiment_readout(self.scenario(treatment_order_value=2))
        self.assertTrue(result["checks"]["conversion"])
        self.assertTrue(result["checks"]["retention"])
        self.assertFalse(result["checks"]["revenue"])
        self.assertLess(result["revenue"]["ci_high"], -1)
        self.assertEqual(result["decision"], "hold")

    def test_srm_blocks_conversion_gain(self):
        result = experiment_readout(self.scenario(treatment_users=1000))
        self.assertTrue(result["checks"]["conversion"])
        self.assertFalse(result["checks"]["sample_ratio"])
        self.assertEqual(result["decision"], "hold")

    def test_all_gates_required_for_review(self):
        result = experiment_readout(self.scenario())
        self.assertTrue(all(result["checks"].values()))
        self.assertEqual(result["decision"], "eligible_for_rollout_review")

    def test_inconclusive_harm_still_blocks(self):
        result = experiment_readout(self.scenario(control_retention=.5, treatment_retention=.5))
        self.assertEqual(result["retention"]["absolute_lift"], 0)
        self.assertFalse(result["checks"]["retention"])
        self.assertEqual(result["decision"], "hold")

    def test_revenue_uses_all_assigned_users_and_matches_welch(self):
        conn = self.scenario()
        result = experiment_readout(conn)
        self.assertEqual(result["revenue"]["control_mean"], 20)
        self.assertEqual(result["revenue"]["treatment_mean"], 50)
        oracle = ttest_ind([100] * 250 + [0] * 250, [100] * 100 + [0] * 400, equal_var=False).confidence_interval()
        self.assertAlmostEqual(result["revenue"]["ci_low"], oracle.low)
        self.assertAlmostEqual(result["revenue"]["ci_high"], oracle.high)

    def test_wilson_interval_matches_scipy(self):
        for count in (0, 1, 20, 99, 100):
            oracle = binomtest(count, 100).proportion_ci(method="wilson")
            low, high = _wilson(count, 100, .05)
            self.assertAlmostEqual(low, oracle.low)
            self.assertAlmostEqual(high, oracle.high)

    def test_difference_interval_symmetry_and_zero_variance(self):
        a = pd.Series([1] * 30 + [0] * 70)
        b = pd.Series([1] * 50 + [0] * 50)
        forward, reverse = _binary_result(a, b, .05), _binary_result(b, a, .05)
        self.assertAlmostEqual(forward["ci_low"], -reverse["ci_high"])
        zero = _binary_result(pd.Series([0] * 100), pd.Series([0] * 100), .05)
        self.assertLess(zero["ci_low"], 0)
        self.assertGreater(zero["ci_high"], 0)
        self.assertIsNone(zero["p_value"])

    def test_inactive_users_stay_in_retention_denominator(self):
        result = cohort_retention(self.scenario(control_users=10, treatment_users=10))
        self.assertEqual(result.iloc[0]["eligible_7d_users"], 20)
        self.assertEqual(result.iloc[0]["retained_7d_users"], 10)
        self.assertEqual(result.iloc[0]["retention_7d"], .5)

    def test_immature_users_excluded_even_when_they_purchase(self):
        conn = self.scenario()
        conn.execute("UPDATE experiment_assignments SET assigned_at='2026-02-28T00:00:00' WHERE user_id=1")
        conn.execute("UPDATE events SET event_time='2026-02-28T12:00:00' WHERE user_id=1")
        result = experiment_readout(conn)
        self.assertEqual(result["excluded_immature_users"], 1)
        self.assertEqual(result["conversion"]["control_users"], 499)
        self.assertEqual(result["conversion"]["control_purchases"], 99)

    def test_windows_reject_pre_assignment_and_boundary_events(self):
        conn = self.scenario(control_users=10, treatment_users=10, control_conversion=0, treatment_conversion=0)
        for event_id, timestamp in ((1001, "2025-12-31T23:59:59"), (1002, "2026-01-08T00:00:00"), (1003, "2026-04-01T00:00:00")):
            conn.execute("INSERT INTO events VALUES (?, 1, 'purchase', ?, 999)", (event_id, timestamp))
        metrics = experiment_user_metrics(conn)
        self.assertEqual(metrics.purchased.sum(), 0)
        self.assertEqual(metrics.revenue.sum(), 0)
        conn.execute("INSERT INTO events VALUES (1004, 1, 'purchase', '2026-01-07T23:59:59', 7)")
        self.assertEqual(experiment_user_metrics(conn).revenue.sum(), 7)

    def test_followup_boundary_is_inclusive_for_eligibility(self):
        conn = self.scenario()
        result = experiment_readout(conn, replace(DEFAULT_POLICY, as_of="2026-01-09"))
        self.assertEqual(result["eligible_users"], 1000)
        result = experiment_readout(conn, replace(DEFAULT_POLICY, as_of="2026-01-08"))
        self.assertEqual(result["eligible_users"], 0)
        self.assertEqual(result["decision"], "hold")
        cohorts = cohort_retention(conn, "2026-01-08")
        self.assertEqual(cohorts.iloc[0]["eligible_7d_users"], 0)
        self.assertTrue(pd.isna(cohorts.iloc[0]["retention_7d"]))

    def test_unrelated_experiment_does_not_change_result(self):
        conn = self.scenario()
        before = experiment_readout(conn)
        conn.execute("INSERT INTO experiment_assignments VALUES (1, 'unrelated', 'bogus', 'invalid')")
        self.assertEqual(experiment_readout(conn), before)

    def test_duplicate_assignment_is_rejected(self):
        conn = self.scenario()
        conn.execute("INSERT INTO experiment_assignments SELECT * FROM experiment_assignments WHERE user_id=1")
        with self.assertRaisesRegex(ValueError, "one assignment"):
            experiment_readout(conn)

    def test_invalid_assignment_and_activity_timestamps_are_rejected(self):
        for table, column in (("experiment_assignments", "assigned_at"), ("events", "event_time"), ("sessions", "session_started_at")):
            with self.subTest(table=table):
                conn = self.scenario()
                conn.execute(f"UPDATE {table} SET {column}='invalid' WHERE user_id=1")
                with self.assertRaisesRegex(ValueError, "timestamp"):
                    experiment_readout(conn)

    def test_zero_revenue_variance_blocks_and_small_sample_blocks(self):
        result = experiment_readout(self.scenario(control_order_value=0, treatment_order_value=0))
        self.assertIsNone(result["revenue"]["ci_low"])
        self.assertFalse(result["checks"]["revenue"])
        result = experiment_readout(self.scenario(control_users=20, treatment_users=20))
        self.assertFalse(result["checks"]["minimum_sample"])
        self.assertEqual(result["decision"], "hold")

    def test_duplicate_event_is_rejected(self):
        conn = self.scenario()
        conn.execute("INSERT INTO events SELECT * FROM events WHERE user_id=1")
        with self.assertRaisesRegex(ValueError, "Duplicate event"):
            experiment_readout(conn)

    def test_missing_revenue_is_not_silently_zero(self):
        conn = self.scenario()
        conn.execute("UPDATE events SET revenue=NULL WHERE user_id=1")
        with self.assertRaisesRegex(ValueError, "finite numeric"):
            experiment_readout(conn)

    def test_empty_missing_arm_and_zero_conversion_do_not_crash(self):
        for config in ({"control_users": 0, "treatment_users": 0}, {"control_users": 0}, {"control_conversion": 0, "treatment_conversion": 0}):
            with self.subTest(config=config):
                conn = self.scenario(**config)
                result = experiment_readout(conn)
                self.assertEqual(result["decision"], "hold")
                self.assertIsNone(result["conversion"]["relative_lift_percent"])
                self.assertIn("Hold rollout", build_markdown_report(conn))

    def test_expected_allocation_is_configurable(self):
        result = experiment_readout(self.scenario(treatment_users=1000), replace(DEFAULT_POLICY, expected_treatment_share=2 / 3))
        self.assertTrue(result["checks"]["sample_ratio"])

    def test_policy_rejects_invalid_values(self):
        for override in ({"as_of": "bad"}, {"alpha": 0}, {"retention_loss_tolerance": -1}, {"revenue_loss_tolerance": math.inf}, {"conversion_days": 1.5}, {"min_users_per_arm": 1}, {"retention_start_day": 8}):
            with self.subTest(override=override), self.assertRaises(ValueError):
                ExperimentPolicy(**override)


if __name__ == "__main__":
    unittest.main()
