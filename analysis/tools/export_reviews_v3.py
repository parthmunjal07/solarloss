"""Repository-root entry point for the V3 V2-result exporter."""

from pathlib import Path
import sys

ANALYSIS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ANALYSIS_DIR / "src"))

from solarloss_research.export_reviews_v3 import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
