from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analytics import ExperimentPolicy, experiment_readout
from src.scenarios import SCENARIOS, scenario_database


def main() -> None:
    policy = ExperimentPolicy(**json.loads((ROOT / "config" / "experiment_policy.json").read_text(encoding="utf-8")))
    results = {}
    lines = ["# Guardrail stress scenarios", "",
             "These constructed fixtures test decision behavior. They do not estimate real-world performance.", "",
             "| Scenario | Eligible users | Conversion difference | Conversion gate | Retention gate | Revenue gate | Sample ratio | Decision |",
             "| --- | ---: | ---: | --- | --- | --- | --- | --- |"]
    for name, parameters in SCENARIOS.items():
        conn = scenario_database(**parameters)
        try:
            result = experiment_readout(conn, policy)
        finally:
            conn.close()
        results[name] = {"scenario_parameters": parameters, **result}
        gates = result["checks"]
        lines.append(f"| {name} | {result['eligible_users']} | {result['conversion']['absolute_lift']:.2%} | {gates['conversion']} | {gates['retention']} | {gates['revenue']} | {gates['sample_ratio']} | {result['decision']} |")
        print(f"{name}: {result['decision']}; {gates}")
    output = ROOT / "outputs"
    output.mkdir(exist_ok=True)
    (output / "guardrail_scenarios.json").write_text(json.dumps(results, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (output / "guardrail_scenarios.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
