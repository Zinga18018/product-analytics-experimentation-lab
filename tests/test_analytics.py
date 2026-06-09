from __future__ import annotations

import sqlite3
import unittest

from src.analytics import ab_test_purchase_result, channel_performance, cohort_retention, funnel_by_variant, table_counts
from src.data_generator import GenerationConfig, generate_product_data, write_sqlite


class ProductAnalyticsTests(unittest.TestCase):
    def setUp(self) -> None:
        tables = generate_product_data(GenerationConfig(users=400, days=30, seed=42))
        self.conn = sqlite3.connect(":memory:")
        for name, frame in tables.items():
            frame.to_sql(name, self.conn, index=False)

    def tearDown(self) -> None:
        self.conn.close()

    def test_table_counts(self) -> None:
        counts = table_counts(self.conn)
        self.assertEqual(counts["users"], 400)
        self.assertEqual(counts["experiment_assignments"], 400)
        self.assertGreater(counts["sessions"], 400)
        self.assertGreater(counts["events"], counts["sessions"])

    def test_funnel_and_ab_result(self) -> None:
        funnel = funnel_by_variant(self.conn)
        self.assertEqual(set(funnel["variant"]), {"control", "treatment"})
        result = ab_test_purchase_result(self.conn)
        self.assertGreaterEqual(result["p_value"], 0)
        self.assertLessEqual(result["p_value"], 1)
        self.assertIn("relative_lift_percent", result)

    def test_channel_and_retention_outputs(self) -> None:
        channels = channel_performance(self.conn)
        retention = cohort_retention(self.conn)
        self.assertIn("revenue_per_user", channels.columns)
        self.assertIn("retention_7d", retention.columns)
        self.assertFalse(channels.empty)
        self.assertFalse(retention.empty)


if __name__ == "__main__":
    unittest.main()
