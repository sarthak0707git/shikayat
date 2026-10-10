"""The buckets a complaint can land in, and the places it can happen.

Read from the DB at runtime (api.db mirrors this table at startup), so a category
promoted from an "Other" suggestion works immediately with no code change.
"""

# name -> (domain, authority, required_fields)
# One common mess on campus, so Mess categories need `meal` only, never a building.
CATEGORIES = {
    "Electrical & AC":    ("Hostel",   "Hostel Office",   ["building", "spot"]),
    "Plumbing & Water":   ("Hostel",   "Hostel Office",   ["building", "spot"]),
    "Furniture & Doors":  ("Hostel",   "Hostel Office",   ["building", "spot"]),
    "Housekeeping":       ("Hostel",   "Hostel Office",   ["building", "spot"]),
    "Food Quality":       ("Mess",     "Mess Committee",  ["meal"]),
    "Hygiene":            ("Mess",     "Mess Committee",  ["meal"]),
    "Service & Timings":  ("Mess",     "Mess Committee",  []),
    "Wi-Fi & LAN":        ("IT",       "IT Cell",         ["building", "spot"]),
    "Portals & Accounts": ("IT",       "IT Cell",         []),
    "Classrooms & Labs":  ("Academic", "Academic Office", ["building", "spot"]),
    "Water Coolers":      ("Campus",   "Estate Office",   ["spot"]),
    "Roads & Lights":     ("Campus",   "Estate Office",   ["spot"]),
    "Transport":          ("Campus",   "Transport Cell",  ["spot"]),
    "Animals & Safety":   ("Campus",   "Estate Office",   ["spot"]),
    "Other":              ("Other",    "Admin",           []),
}

# Real IIT Bhilai places. One common mess; academic rooms are not named further.
BUILDINGS = [
    "BH1 (Kanhar)",
    "BH2 (Gopad)",
    "GH1 (Indravati)",
    "MSH (Married Hostel)",
    "Mess",
    "Academic Building",
]

# The mess is the only one, so Gemma never has to ask which.
DEFAULT_MESS = "Mess"

MEALS = ["breakfast", "lunch", "snacks", "dinner"]
SEVERITIES = ["urgent", "high", "medium", "low"]
SEVERITY_WEIGHT = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
STATUSES = ["open", "in_progress", "resolved"]
LANGUAGES = ["en", "hinglish", "hi"]

ESCALATE_AT = 5  # reports


def rows_for_db():
    """The `categories` table contents, in a stable order."""
    return [
        {"name": name, "domain": domain, "authority": authority, "required_fields": fields}
        for name, (domain, authority, fields) in CATEGORIES.items()
    ]


def priority(report_count, severity):
    return report_count * SEVERITY_WEIGHT.get(severity, 1)


def is_escalated(report_count, severity):
    return report_count >= ESCALATE_AT or severity == "urgent"
