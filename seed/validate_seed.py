"""Validate seed/complaints.json against every hard rule from issue #6.

    python seed/validate_seed.py        # PASS/FAIL per rule, exit 1 if any FAIL

Stdlib only: json, re, datetime, sys, pathlib.
"""
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

SEED = Path(__file__).resolve().parent / "complaints.json"

# (category, required building?, required spot?) per issue #6 allowed values
CATEGORY_NEEDS = {
    "Electrical & AC": ("building", "spot"),
    "Plumbing & Water": ("building", "spot"),
    "Furniture & Doors": ("building", "spot"),
    "Housekeeping": ("building", "spot"),
    "Food Quality": ("meal",),
    "Hygiene": ("meal",),
    "Service & Timings": (),
    "Wi-Fi & LAN": ("building", "spot"),
    "Portals & Accounts": (),
    "Classrooms & Labs": ("building", "spot"),
    "Water Coolers": ("spot",),
    "Roads & Lights": ("spot",),
    "Transport": ("spot",),
    "Animals & Safety": ("spot",),
    "Other": (),
}
BUILDINGS = {"BH1 (Kanhar)", "BH2 (Gopad)", "GH1 (Indravati)",
             "MSH (Married Hostel)", "Mess", "Academic Building"}
SEVERITIES = {"urgent", "high", "medium", "low"}
STATUSES = {"open", "in_progress", "resolved"}
MEALS = {"breakfast", "lunch", "snacks", "dinner"}
LANGUAGES = {"en", "hinglish", "hi"}
WEIGHT = {"urgent": 4, "high": 3, "medium": 2, "low": 1}

DEMO_SUMMARY = "Hair and flies found in mess food"
ROOM_RE = re.compile(r"^[A-Z]\d{3}$")
# a spot is ok if it is a room code or names a floor / place a technician can walk to
PLACE_WORDS = ("floor", "wing", "washroom", "corridor", "balcony", "common room",
               "entrance", "gate", "road", "walkway", "lobby", "lab", "hall",
               "stop", "ground", "mess", "library", "canteen", "gym")
START, END = date(2026, 9, 27), date(2026, 10, 10)

results = []


def check(rule, ok, msg):
    results.append((f"{'PASS' if ok else 'FAIL'}  rule {rule}: {msg}", ok))


def main():
    data = json.loads(SEED.read_text(encoding="utf-8"))
    complaints = data["complaints"]
    reports_all = [r for c in complaints for r in c["reports"]]
    n = len(complaints)

    check(1, 43 <= n <= 47 and 115 <= len(reports_all) <= 125,
          f"counts in band: {n} complaints, {len(reports_all)} reports (want 43-47 / 115-125)")

    bad_dates = []
    for r in reports_all:
        raw = r["created_at"]
        if not raw.endswith("+05:30"):
            bad_dates.append(raw)
            continue
        if not (START <= datetime.fromisoformat(raw).date() <= END):
            bad_dates.append(raw)
    check(2, not bad_dates,
          "all created_at in 27 Sep - 10 Oct with +05:30"
          + (f" -- bad: {bad_dates[:3]}" if bad_dates else ""))

    counts = sorted(len(c["reports"]) for c in complaints)
    dominant = [c for c in complaints if 6 <= len(c["reports"]) <= 14]
    overlong = [c["summary"] for c in complaints if len(c["reports"]) > 14]
    check(3, len(dominant) in (5, 6) and not overlong,
          f"5-6 dominant issues with 6-14 reports: {len(dominant)} dominant"
          + (f", overlong: {overlong}" if overlong else ""))

    resolved = [c for c in complaints if c["status"] == "resolved"]
    inprog = [c for c in complaints if c["status"] == "in_progress"]
    no_note = [c["summary"] for c in resolved if not c.get("resolution_note")]
    check(4, len(resolved) == 4 and len(inprog) == 3 and not no_note,
          f"4 resolved (with notes) + 3 in_progress: {len(resolved)} / {len(inprog)}"
          + (f", missing note: {no_note}" if no_note else ""))

    others = [c for c in complaints if c["category"] == "Other"]
    sugg = sorted(c.get("suggested_category") for c in others)
    check(5, sugg == ["Gym", "Laundry", "Laundry", "Laundry"],
          f"4 Other: Laundry x3 + Gym x1, got {sugg}")

    demos = [c for c in complaints
             if c["category"] == "Hygiene" and c["building"] == "Mess"
             and c["severity"] == "high" and c["status"] == "open"
             and c["summary"] == DEMO_SUMMARY]
    check(6, len(demos) == 1 and len(demos[0]["reports"]) == 4,
          "demo mess-hygiene complaint present exactly once with exactly 4 reports")

    bh2 = [c["summary"] for c in complaints
           if c["building"] == "BH2 (Gopad)"
           and c["category"] in ("Electrical & AC", "Plumbing & Water")]
    check(7, not bh2, f"no BH2 (Gopad) electrical/plumbing" + (f" -- found: {bh2}" if bh2 else ""))

    hin = sum(1 for r in reports_all if r["language"] in ("hinglish", "hi"))
    share = hin / max(len(reports_all), 1)
    check(8, share >= 0.40, f">=40% Hinglish/Hindi raw_text: {share:.0%} ({hin}/{len(reports_all)})")

    long_summ = [c["summary"] for c in complaints if len(c["summary"].split()) > 12]
    check(9, not long_summ, f"summary <= 12 words" + (f" -- too long: {long_summ}" if long_summ else ""))

    # ---- allowed values and required fields ----
    bad_cat = [c["summary"] for c in complaints if c["category"] not in CATEGORY_NEEDS]
    bad_bld = [c["summary"] for c in complaints
               if c["building"] is not None and c["building"] not in BUILDINGS]
    bad_sev = [c["summary"] for c in complaints if c["severity"] not in SEVERITIES]
    bad_sts = [c["summary"] for c in complaints if c["status"] not in STATUSES]
    bad_meal = [c["summary"] for c in complaints
                if c["meal"] is not None and c["meal"] not in MEALS]
    bad_lang = [r["raw_text"] for r in reports_all if r["language"] not in LANGUAGES]
    bad_spot = [c["summary"] for c in complaints
                if c["spot"] is not None and not (
                    ROOM_RE.match(c["spot"])
                    or any(w in c["spot"].lower() for w in PLACE_WORDS))]
    missing = []
    for c in complaints:
        for field in CATEGORY_NEEDS.get(c["category"], ()):
            if c.get(field) is None:
                missing.append(f"{c['summary']} (missing {field})")
    bad_other = [c["summary"] for c in complaints
                 if c["category"] == "Other" and not c.get("suggested_category")]
    ok_values = not any((bad_cat, bad_bld, bad_sev, bad_sts, bad_meal,
                         bad_lang, bad_spot, missing, bad_other))
    detail = "; ".join(
        f"{name}: {bad[:2]}" for name, bad in (
            ("category", bad_cat), ("building", bad_bld), ("severity", bad_sev),
            ("status", bad_sts), ("meal", bad_meal), ("language", bad_lang),
            ("spot", bad_spot), ("required", missing), ("suggested", bad_other)) if bad)
    check(10, ok_values,
          "all values from allowed lists, spot is room code or place, required fields present"
          + (f" -- {detail}" if detail else ""))

    for line, ok in results:
        print(line)
    failed = sum(1 for _, ok in results if not ok)
    print(f"\n{len(results) - failed}/{len(results)} rules passed" + ("  FAIL" if failed else "  PASS"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
