#!/usr/bin/env python3
"""Check a Shikayat triage result: is every required field there, and legal?

Usage:
    python skills/campus-complaint-triage/scripts/triage_check.py '{"category": ...}'
    python skills/campus-complaint-triage/scripts/triage_check.py result.json
    echo '{"category": ...}' | python skills/campus-complaint-triage/scripts/triage_check.py -

Prints one PASS/FAIL line per check, then OK or FAILED.
Exit codes: 0 = OK, 1 = a check failed, 2 = the input could not be read.

Standard library only. Keep CATEGORIES in sync with references/buckets.md
(and complaints/categories.py).
"""

import json
import re
import sys
from pathlib import Path

# --- the bucket table ------------------------------------------------------
# category -> (domain, authority, required fields, in the order to check them)
CATEGORIES = {
    "Electrical & AC":    ("Hostel",   "Hostel Office",   ("building", "spot")),
    "Plumbing & Water":   ("Hostel",   "Hostel Office",   ("building", "spot")),
    "Furniture & Doors":  ("Hostel",   "Hostel Office",   ("building", "spot")),
    "Housekeeping":       ("Hostel",   "Hostel Office",   ("building", "spot")),
    "Food Quality":       ("Mess",     "Mess Committee",  ("meal",)),
    "Hygiene":            ("Mess",     "Mess Committee",  ("meal",)),
    "Service & Timings":  ("Mess",     "Mess Committee",  ()),
    "Wi-Fi & LAN":        ("IT",       "IT Cell",         ("building", "spot")),
    "Portals & Accounts": ("IT",       "IT Cell",         ()),
    "Classrooms & Labs":  ("Academic", "Academic Office", ("building", "spot")),
    "Water Coolers":      ("Campus",   "Estate Office",   ("spot",)),
    "Roads & Lights":     ("Campus",   "Estate Office",   ("spot",)),
    "Transport":          ("Campus",   "Transport Cell",  ("spot",)),
    "Animals & Safety":   ("Campus",   "Estate Office",   ("spot",)),
    "Other":              ("Other",    "Admin",           ()),
}

BUILDINGS = (
    "BH1 (Kanhar)", "BH2 (Gopad)", "GH1 (Indravati)",
    "MSH (Married Hostel)", "Mess", "Academic Building",
)
MEALS = ("breakfast", "lunch", "snacks", "dinner")
SEVERITIES = ("urgent", "high", "medium", "low")

MAX_SUMMARY_WORDS = 12
ROOM_RE = re.compile(r"^[A-Z]\d{3}$")  # wing + room: E207, B322, F101
# The "f " entry catches "2F", "Block F", "F-wing" (the trailing space is added below).
PLACE_WORDS = ("floor", "f ", "washroom", "corridor", "lobby", "gate", "ground")

# A public summary must not name anyone. Stdlib has no NER, so we use a short
# list of common given names + honorifics, matched case-insensitively on whole
# words. Extend it freely; false negatives are cheap, false positives are not.
PERSONAL_NAMES = frozenset("""
aakash abhishek aditya akansha akash amit ananya anjali arjun ashish
deepak divya gaurav harsh kavya karan kunal manish meera mohit neha nikhil
pooja priya priyanka puja ravi rahul rajesh ramesh ranjan riya rohit sakshi
shreya shivam siddharth sneha sumit suresh tanvi varun vishal yash
alice christopher daniel david emma james joseph john michael robert sarah thomas
mr mrs ms dr prof sir madam miss
""".split())

USAGE = "usage: triage_check.py '<json>' | <file.json> | -   (- reads stdin)"


# --- small helpers ---------------------------------------------------------

def is_present(data, field):
    """True when the field holds a non-empty string."""
    value = data.get(field)
    return isinstance(value, str) and value.strip() != ""


def is_specific_spot(spot):
    """A spot a technician can walk to: E207, or a floor/place description."""
    spot = spot.strip()
    if ROOM_RE.fullmatch(spot):
        return True
    haystack = spot.lower() + " "  # so a trailing "F"/"2F" also matches "f "
    return any(word in haystack for word in PLACE_WORDS)


def find_personal_name(summary):
    """The first name-looking word in the summary, or None."""
    for token in summary.split():
        word = token.strip(".,!?;:'\"()").lower()
        if word in PERSONAL_NAMES:
            return token.strip(".,!?;:'\"()")
    return None


# --- the checks ------------------------------------------------------------

class Checker:
    def __init__(self):
        self.failed = False

    def line(self, ok, message):
        print(("PASS  " if ok else "FAIL  ") + message)
        if not ok:
            self.failed = True

    # -- one check per field

    def check_category(self, data):
        category = data.get("category")
        if category is None or (isinstance(category, str) and not category.strip()):
            self.line(False, "category missing (expected one of the 15 buckets)")
            return None
        entry = CATEGORIES.get(category) if isinstance(category, str) else None
        if entry is None:
            self.line(False, f"category {category!r} is not one of the 15 buckets")
            return None
        domain, authority, required = entry
        self.line(True, f'category "{category}" exists (domain {domain}, authority {authority})')
        return (domain, authority, required)

    def check_field(self, data, field, required):
        """Check one of building/spot/meal. Returns True when it is fine."""
        if not is_present(data, field):
            if required:
                self.line(False, f"required field {field} missing or empty")
            return False
        value = data[field].strip()
        if field == "building":
            ok, bad = value in BUILDINGS, "not a known building"
            why = f'(expected one of: {", ".join(BUILDINGS)})'
            good = f"required field building present: \"{value}\"" if required \
                else f"building \"{value}\" is a known building"
        elif field == "spot":
            ok, bad = is_specific_spot(value), "too vague"
            why = '(expected wing+room like E207, or a place like "2F washroom")'
            good = f"required field spot present and specific: \"{value}\"" if required \
                else f"spot \"{value}\" is specific"
        else:  # field == "meal"
            ok, bad = value in MEALS, "not a valid meal"
            why = f'(expected {"|".join(MEALS)})'
            good = f"required field meal present: \"{value}\"" if required \
                else f"meal \"{value}\" is valid"
        if ok:
            self.line(True, good)
        else:
            self.line(False, f"{field} is present but {bad}: \"{value}\" {why}")
        return ok

    def check_severity(self, data):
        severity = data.get("severity")
        if not isinstance(severity, str) or not severity.strip():
            self.line(False, f'severity missing (expected {"|".join(SEVERITIES)})')
        elif severity not in SEVERITIES:
            self.line(False, f'severity "{severity}" is not valid '
                       f'(expected {"|".join(SEVERITIES)})')
        else:
            self.line(True, f'severity "{severity}" is valid')

    def check_summary(self, data):
        summary = data.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            self.line(False, "summary missing or empty (English, <= 12 words, no names)")
            return
        words = summary.split()
        name = find_personal_name(summary)
        problems = 0
        if len(words) > MAX_SUMMARY_WORDS:
            self.line(False, f"summary is {len(words)} words (> {MAX_SUMMARY_WORDS})")
            problems += 1
        if name:
            self.line(False, f'summary must not name a person: "{name}" '
                       "(it is shown publicly)")
            problems += 1
        if not problems:
            self.line(True, f"summary is {len(words)} words "
                       f"(<= {MAX_SUMMARY_WORDS}) and has no personal name")


def run(data):
    checker = Checker()
    picked = checker.check_category(data)
    required = picked[2] if picked else ()
    for field in ("building", "spot", "meal"):
        checker.check_field(data, field, field in required)
    checker.check_severity(data)
    checker.check_summary(data)
    print("FAILED" if checker.failed else "OK")
    return 1 if checker.failed else 0


# --- input -----------------------------------------------------------------

def read_argument(argv):
    """Return the raw JSON text, or None after explaining a usage/IO error."""
    if len(argv) == 2 and argv[1] in ("-h", "--help"):
        print(USAGE)
        return None
    if len(argv) != 2:
        sys.stderr.write(f"triage_check: expected exactly one argument\n{USAGE}\n")
        sys.exit(2)
    argument = argv[1]
    if argument == "-":
        return sys.stdin.read()
    path = Path(argument)
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    except OSError as error:
        sys.stderr.write(f"triage_check: cannot read {argument}: {error}\n")
        sys.exit(2)
    return argument  # inline JSON


def main(argv):
    raw = read_argument(argv)
    if raw is None:  # --help
        return 0
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        checker = Checker()
        hint = " (if that was a file path, the file does not exist)" \
            if "{" not in raw else ""
        checker.line(False, f"input is not valid JSON: {error.msg}{hint}")
        print("FAILED")
        return 1
    if not isinstance(data, dict):
        checker = Checker()
        checker.line(False, "input is a JSON value, but an object like "
                     '{"category": ...} was expected')
        print("FAILED")
        return 1
    return run(data)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
