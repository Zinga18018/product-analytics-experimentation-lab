from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data_generator import GenerationConfig, build_database


def main() -> None:
    db_path = ROOT / "data" / "product_analytics.sqlite"
    counts = build_database(db_path, GenerationConfig())
    print(f"wrote {db_path}")
    for table, count in counts.items():
        print(f"{table}: {count}")


if __name__ == "__main__":
    main()
