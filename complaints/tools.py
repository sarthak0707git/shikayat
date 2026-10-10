"""The five tools Gemma is allowed to ask for, and the limits our code puts on them.

Gemma decides *within* the rules; the rules themselves are enforced here:

  - it never passes a complaint id we did not just show it (no hallucinated merges)
  - it never asks a student more than two questions
  - it never sets priority or escalation (api/db.py computes those)
  - it never invents a category (unknown categories become Other + a suggestion)

The tool functions take only flat str/int params, because that is all the harness's
@tool decorator allows. Everything about the report that Gemma must not be trusted to
repeat back - the thread id, the raw text, the photo path - is read from a contextvar
set by complaints/agent.py before the run.
"""

import contextvars
import json
import re

from api import db
from complaints import categories as cats
from harness import tool

MAX_QUESTIONS = 2

# The report currently being triaged. complaints/agent.py sets this.
CURRENT = contextvars.ContextVar("current_report")

PLACE_WORDS = ("floor", "washroom", "bathroom", "toilet", "corridor", "lobby", "gate", "ground",
               "balcony", "stair", "mess", "hall", "lab", "room", "wing", "kitchen", "counter",
               "canteen", "library", "gym", "road", "park", "stop", "block", "entrance")
ROOM_PATTERN = re.compile(r"^[A-Za-z]-?\d{2,4}$")  # E207, B322, F101, LH-2


def context():
    """The report being triaged, or an empty stand-in so a stray call cannot crash."""
    try:
        return CURRENT.get()
    except LookupError:
        return new_context("", None, None)


def new_context(raw_text, photo_path=None, thread_id=None):
    """A fresh triage context. Returned so the caller can keep a handle on it."""
    return {
        "thread_id": thread_id,
        "raw_text": raw_text,
        "photo_path": photo_path,
        "language": None,
        "questions_asked": 0,
        "followups": [],          # [{"q": ..., "a": ...}]
        "candidate_ids": set(),   # ids find_similar actually showed Gemma
        "outcome": None,          # filed | merged | rejected
        "complaint": None,        # the Complaint dict we ended up with
        "message": None,          # the sentence shown to the student
        "pending_question": None,
    }


def spot_is_specific(spot):
    """True if a technician could walk to it. 'my room' and 'upstairs' cannot."""
    if not spot:
        return False
    text = spot.strip()
    if len(text) < 3:
        return False
    if ROOM_PATTERN.match(text):
        return True
    low = text.lower()
    if low in ("my room", "upstairs", "downstairs", "here", "hostel", "room"):
        return False
    return any(word in low for word in PLACE_WORDS) or bool(re.search(r"\d", low))


def resolve_category(name):
    """The category row for `name`, or the Other row when Gemma invents one."""
    found = db.get_category(name)
    return found or db.get_category("Other")


def missing_for(category_row, building, spot, meal):
    """Which required fields are still missing, applying the one-mess rule."""
    have = {"building": (building or "").strip(), "spot": (spot or "").strip(),
            "meal": (meal or "").strip().lower()}
    if category_row["domain"] == "Mess":
        have["building"] = have["building"] or cats.DEFAULT_MESS  # only one mess on campus
    missing = []
    for field in category_row["required_fields"]:
        value = have.get(field, "")
        if not value:
            missing.append(field)
        elif field == "spot" and not spot_is_specific(value):
            missing.append("spot")
        elif field == "meal" and value not in cats.MEALS:
            missing.append("meal")
    return missing


# ---------- 1. look before you leap ----------

@tool
def find_similar(category: str, building: str = "", spot: str = "", meal: str = ""):
    """Find open complaints that might already cover this report. Always call this first.

    category: the category you picked, exactly as written in the category list
    building: the hostel, mess or block, or "" if the student did not say
    spot: the wing+room (E207) or the shared place (2F washroom), or "" if not said
    meal: breakfast, lunch, snacks or dinner, or "" if this is not a mess issue
    """
    ctx = context()
    row = resolve_category(category)
    if row["domain"] == "Mess":
        building = building or cats.DEFAULT_MESS

    candidates = db.find_open(row["name"], building or None)
    ctx["candidate_ids"] = {c["id"] for c in candidates}

    return json.dumps({
        "category": row["name"],
        "domain": row["domain"],
        "authority": row["authority"],
        "required_fields": row["required_fields"],
        "missing_fields": missing_for(row, building, spot, meal),
        "questions_already_asked": ctx["questions_asked"],
        "questions_left": max(0, MAX_QUESTIONS - ctx["questions_asked"]),
        "open_complaints": [
            {"id": c["id"], "summary": c["summary"], "building": c["building"], "spot": c["spot"],
             "meal": c["meal"], "severity": c["severity"], "report_count": c["report_count"],
             "last_reported_at": c["last_reported_at"]}
            for c in candidates
        ],
    }, ensure_ascii=False)


# ---------- 2. file it ----------

@tool(stop=True)
def file_new(category: str, severity: str, summary: str, details: str = "", building: str = "",
             spot: str = "", meal: str = "", language: str = "", suggested_category: str = ""):
    """File this as a brand new complaint. Use when nothing open already covers it.

    category: the category, exactly as written in the category list
    severity: urgent, high, medium or low
    summary: neutral English, 12 words or fewer, no names - this is shown publicly
    details: one or two English sentences, including what the photo shows if there is one
    building: the hostel, mess or block, or "" if this category does not need one
    spot: the wing+room (E207) or the shared place (2F washroom), or ""
    meal: breakfast, lunch, snacks or dinner, or ""
    language: the language the student wrote in - en, hinglish or hi
    suggested_category: if you had to use Other, the category this should belong to
    """
    ctx = context()
    severity = (severity or "").strip().lower()
    if severity not in cats.SEVERITIES:
        return f"Error: severity must be one of {', '.join(cats.SEVERITIES)}."
    if not (summary or "").strip():
        return "Error: write a short neutral summary of 12 words or fewer."

    row = resolve_category(category)
    if row["domain"] == "Mess":
        building = building or cats.DEFAULT_MESS

    missing = missing_for(row, building, spot, meal)
    if missing and ctx["questions_asked"] < MAX_QUESTIONS:
        return (f"Error: {row['name']} needs {', '.join(missing)} before it can be filed. "
                f"Call ask_student for the missing details first.")

    complaint = db.create_complaint({
        "category": row["name"], "building": building or None, "spot": spot or None,
        "meal": (meal or "").strip().lower() or None, "summary": summary.strip(),
        "details": (details or "").strip() or None, "severity": severity,
        "needs_details": bool(missing),
        "suggested_category": (suggested_category or "").strip() or None,
        "report": {"thread_id": ctx["thread_id"], "raw_text": ctx["raw_text"],
                   "language": (language or "").strip().lower() or None,
                   "photo_path": ctx["photo_path"], "outcome": "filed",
                   "followups": ctx["followups"]},
    })
    ctx.update(outcome="filed", complaint=complaint)
    note = " We have flagged it as needing more details." if missing else ""
    ctx["message"] = (f"Filed as #{complaint['id']} in the {complaint['authority']} queue.{note}")
    return (f"Filed complaint #{complaint['id']} ({complaint['category']}, {complaint['severity']}) "
            f"for {complaint['authority']}.{note}")


# ---------- 3. or merge it ----------

@tool(stop=True)
def merge_into(complaint_id: int, severity: str, reason: str, details: str = ""):
    """Add this report to an open complaint you just saw in find_similar.

    complaint_id: the id of that complaint, copied from the find_similar result
    severity: urgent, high, medium or low for THIS report - it can raise the complaint, never lower it
    reason: one short English line saying why it is the same issue
    details: anything this report adds, especially what a photo shows
    """
    ctx = context()
    if complaint_id not in ctx["candidate_ids"]:
        return (f"Error: #{complaint_id} was not in the last find_similar result. "
                "Only merge into a complaint you were just shown, or call file_new.")
    severity = (severity or "").strip().lower()
    if severity and severity not in cats.SEVERITIES:
        return f"Error: severity must be one of {', '.join(cats.SEVERITIES)}."

    try:
        complaint = db.add_report(complaint_id, {
            "thread_id": ctx["thread_id"], "raw_text": ctx["raw_text"],
            "photo_path": ctx["photo_path"], "severity": severity or None,
            "outcome": "merged", "merge_reason": (reason or "").strip() or "Same issue",
            "followups": ctx["followups"],
        })
    except ValueError as error:
        return f"Error: {error}"

    ctx.update(outcome="merged", complaint=complaint)
    count = complaint["report_count"]
    ordinal = {1: "1st", 2: "2nd", 3: "3rd"}.get(count, f"{count}th")
    escalated = " This complaint is now escalated." if complaint["escalated"] else ""
    ctx["message"] = (f"Added to #{complaint['id']}. You're the {ordinal} student to report this."
                      f"{escalated}")
    return (f"Merged into #{complaint['id']}. It now has {count} reports, severity "
            f"{complaint['severity']}, escalated={complaint['escalated']}.")


# ---------- 4. or ask the student ----------

@tool(pause=True)
def ask_student(question: str, reason: str = "missing_fields"):
    """Ask the student one short question, in the language they wrote in.

    question: one short sentence. Ask for every missing detail at once, not one at a time.
    reason: missing_fields if a required detail is absent, ambiguous_duplicate if you cannot tell
            whether this is an existing complaint or a new one
    """
    ctx = context()
    if ctx["questions_asked"] >= MAX_QUESTIONS:
        return (f"Error: you have already asked {MAX_QUESTIONS} questions. Decide now with what "
                "you have - call file_new, merge_into or reject.")
    question = (question or "").strip()
    if not question:
        return "Error: write the question you want to ask the student."

    ctx["questions_asked"] += 1
    ctx["followups"].append({"q": question, "a": None})
    ctx["pending_question"] = question
    return question


# ---------- 5. or throw it away ----------

@tool(stop=True)
def reject(reason: str):
    """Reject this report: it is not a campus problem, or it is gibberish, abuse or a test.

    reason: one polite sentence for the student, in the language they wrote in
    """
    ctx = context()
    reason = (reason or "").strip() or "This does not look like a campus issue."
    db.create_report({
        "thread_id": ctx["thread_id"], "raw_text": ctx["raw_text"],
        "photo_path": ctx["photo_path"], "outcome": "rejected",
        "merge_reason": reason, "followups": ctx["followups"],
    })
    ctx.update(outcome="rejected", complaint=None, message=reason)
    return f"Rejected and recorded, nothing made public. Reason given: {reason}"


TOOL_NAMES = ["find_similar", "file_new", "merge_into", "ask_student", "reject"]


def label_for(name, args):
    """A sentence a student can read while they wait, for RunResult.steps[].label."""
    if name == "find_similar":
        where = args.get("building") or args.get("spot") or args.get("category") or "the campus"
        return f"Looking for similar reports in {where}"
    if name == "file_new":
        return "Filing a new complaint"
    if name == "merge_into":
        return f"Adding this to complaint #{args.get('complaint_id')}"
    if name == "ask_student":
        return "Asking you for the missing details"
    if name == "reject":
        return "Checking whether this is a campus issue"
    return f"Running {name.replace('_', ' ')}"
