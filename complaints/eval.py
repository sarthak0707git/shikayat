"""Run seed/test_cases.json through the real agent and print a pass/fail table.

    python -m complaints.eval                  # all cases, against a freshly seeded DB
    python -m complaints.eval --case 3         # just case 3
    python -m complaints.eval --no-reset       # keep whatever is in the DB

Each case costs about two Gemma calls, so the whole table is roughly 25 calls.
"""

import argparse
import json
import sys
from pathlib import Path

from api import db, seed
from complaints.agent import handle_report

CASES_FILE = Path(__file__).resolve().parent.parent / "seed" / "test_cases.json"


def check(case, result):
    """Did this result match what the case expected? Returns (ok, what_we_got)."""
    expected = case["expect_outcome"]
    status = result["status"]
    complaint = result.get("complaint") or {}

    if status == "needs_input":
        got = "ask"
    elif status == "merged":
        got = f"merged:{complaint.get('id')}"
    elif status in ("filed", "rejected", "error"):
        got = status
    else:
        got = status

    ok = got == expected
    # A merge into the right complaint is the strict form; "merged" alone also passes.
    if not ok and expected == "merged" and status == "merged":
        ok = True

    wanted_category = case.get("expect_category")
    category = complaint.get("category")
    if ok and wanted_category and status in ("filed", "merged") and category != wanted_category:
        ok = False
        got += f" (category {category}, wanted {wanted_category})"
    return ok, got


def run(cases, reset=True):
    if reset:
        made, reports = seed.load(reset=True)
        print(f"Seeded {made} complaints / {reports} reports\n")
    else:
        db.init_db()

    width = max(len(c["text"]) for c in cases)
    width = min(width, 58)
    print(f"{'#':<3} {'report':<{width}}  {'expected':<12} {'got':<12} ")
    print("-" * (width + 32))

    passed = []
    for number, case in enumerate(cases, 1):
        photo = case.get("photo")
        if photo and not Path(photo).exists():
            photo = None  # the photo has not been taken yet; the text still has to work
        try:
            result = handle_report(case["text"], photo_path=photo)
        except Exception as error:  # a crash is a failure, not a reason to stop the table
            result = {"status": "error", "message": str(error), "complaint": None, "steps": []}
        ok, got = check(case, result)
        passed.append(ok)
        text = case["text"] if len(case["text"]) <= width else case["text"][:width - 1] + "…"
        print(f"{number:<3} {text:<{width}}  {case['expect_outcome']:<12} {got:<12} "
              f"{'PASS' if ok else 'FAIL'}")
        if not ok:
            detail = result.get("question") or result.get("message") or ""
            if detail:
                print(f"    {'':<{width}}  -> {detail[:90]}")

    score = sum(passed)
    print(f"\n{score}/{len(cases)} passed", end="")
    print("   (target is 10/12)" if len(cases) == 12 else "")
    return score, len(cases)


def main():
    parser = argparse.ArgumentParser(description="Score the triage prompt against seed/test_cases.json")
    parser.add_argument("--case", type=int, action="append", default=[],
                        help="run only this case number (repeatable)")
    parser.add_argument("--no-reset", action="store_true", help="do not reseed the database first")
    parser.add_argument("--file", default=str(CASES_FILE))
    args = parser.parse_args()

    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    cases = data["cases"] if isinstance(data, dict) else data
    if args.case:
        cases = [cases[n - 1] for n in args.case if 1 <= n <= len(cases)]

    score, total = run(cases, reset=not args.no_reset)
    return 0 if score >= min(10, total) else 1


if __name__ == "__main__":
    sys.exit(main())
