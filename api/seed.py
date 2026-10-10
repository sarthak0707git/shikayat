"""Load seed/complaints.json straight into SQLite. No Gemma calls.

    python -m api.seed --reset      # wipe the DB and reload
    python -m api.seed              # load into whatever is there
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

from api import db

SEED_FILE = Path(__file__).resolve().parent.parent / "seed" / "complaints.json"


def load(reset=False, path=SEED_FILE):
    db.init_db(reset=reset)
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    complaints = data["complaints"] if isinstance(data, dict) else data
    made = reports_made = 0

    for item in complaints:
        reports = sorted(item.get("reports") or [], key=lambda r: r.get("created_at") or "")
        if not reports:
            continue
        first, rest = reports[0], reports[1:]
        resolved_at = None
        if item.get("status") == "resolved":
            last = datetime.fromisoformat(reports[-1]["created_at"])
            resolved_at = (last + timedelta(days=1)).isoformat()

        complaint = db.create_complaint({
            "category": item["category"], "building": item.get("building"), "spot": item.get("spot"),
            "meal": item.get("meal"), "summary": item["summary"], "details": item.get("details"),
            "severity": item["severity"], "status": item.get("status", "open"),
            "suggested_category": item.get("suggested_category"),
            "resolution_note": item.get("resolution_note"), "resolved_at": resolved_at,
            "report": {**first, "photo_path": first.get("photo_path"), "outcome": "filed"},
        })
        made += 1
        reports_made += 1
        for report in rest:
            db.add_report(complaint["id"], {**report, "outcome": "merged",
                                            "merge_reason": report.get("merge_reason") or "Same issue, same place"})
            reports_made += 1

    return made, reports_made


def main():
    parser = argparse.ArgumentParser(description="Load the seed complaints into SQLite.")
    parser.add_argument("--reset", action="store_true", help="drop the tables first")
    parser.add_argument("--file", default=str(SEED_FILE))
    args = parser.parse_args()
    made, reports = load(reset=args.reset, path=args.file)
    stats = db.stats()
    print(f"Loaded {made} complaints and {reports} reports into {db.DB_PATH}")
    print("KPIs:", stats["kpis"])
    print("Top 3 by priority:")
    for issue in stats["top_issues"][:3]:
        print(f"  #{issue['id']:>2} prio {issue['priority']:>3}  {issue['report_count']}x  "
              f"{issue['severity']:<6} {issue['summary']}")


if __name__ == "__main__":
    main()
