from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analytics import ExperimentPolicy, connect, experiment_readout
from src.reporting import build_markdown_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Read out a fixed-horizon synthetic experiment.")
    parser.add_argument("--policy", type=Path, default=ROOT / "config" / "experiment_policy.json")
    args = parser.parse_args()
    policy = ExperimentPolicy(**json.loads(args.policy.read_text(encoding="utf-8")))
    db_path = ROOT / "data" / "product_analytics.sqlite"
    output_path = ROOT / "outputs" / "analysis_report.md"
    with connect(db_path) as conn:
        report = build_markdown_report(conn, policy)
        readout = experiment_readout(conn, policy)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    (output_path.parent / "experiment_readout.json").write_text(json.dumps(readout, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
