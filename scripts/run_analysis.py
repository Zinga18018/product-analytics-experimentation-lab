from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analytics import connect
from src.reporting import build_markdown_report


def main() -> None:
    db_path = ROOT / "data" / "product_analytics.sqlite"
    output_path = ROOT / "outputs" / "analysis_report.md"
    with connect(db_path) as conn:
        report = build_markdown_report(conn)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
