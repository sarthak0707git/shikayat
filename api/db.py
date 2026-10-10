"""Every SQL statement in the project lives here. No SQL anywhere else.

Priority and escalation are computed in code (never by Gemma):
    priority  = report_count * {urgent:4, high:3, medium:2, low:1}
    escalated = report_count >= 5 or severity == "urgent"
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from complaints import categories as cats

IST = timezone(timedelta(hours=5, minutes=30))
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "shikayat.db"


def now_iso():
    """Current time in IST, ISO 8601 with +05:30, seconds precision."""
    return datetime.now(IST).replace(microsecond=0).isoformat()


def connect():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    authority TEXT NOT NULL,
    required_fields TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    domain TEXT NOT NULL,
    authority TEXT NOT NULL,
    building TEXT,
    spot TEXT,
    meal TEXT,
    summary TEXT NOT NULL,
    details TEXT,
    severity TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'open',
    escalated INTEGER NOT NULL DEFAULT 0,
    needs_details INTEGER NOT NULL DEFAULT 0,
    report_count INTEGER NOT NULL DEFAULT 0,
    suggested_category TEXT,
    first_reported_at TEXT,
    last_reported_at TEXT,
    resolved_at TEXT,
    resolution_note TEXT
);
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER REFERENCES complaints(id),
    thread_id TEXT,
    raw_text TEXT NOT NULL,
    language TEXT,
    photo_path TEXT,
    outcome TEXT,
    merge_reason TEXT,
    followups TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_complaints_cat ON complaints(category, status);
CREATE INDEX IF NOT EXISTS idx_reports_complaint ON reports(complaint_id);
"""


def init_db(reset=False):
    """Create the tables and mirror complaints/categories.py into the categories table."""
    conn = connect()
    with conn:
        if reset:
            conn.executescript("DROP TABLE IF EXISTS reports; DROP TABLE IF EXISTS complaints; DROP TABLE IF EXISTS categories;")
        conn.executescript(SCHEMA)
        for row in cats.rows_for_db():
            conn.execute(
                "INSERT INTO categories (name, domain, authority, required_fields) VALUES (?,?,?,?) "
                "ON CONFLICT(name) DO UPDATE SET domain=excluded.domain, authority=excluded.authority, "
                "required_fields=excluded.required_fields",
                (row["name"], row["domain"], row["authority"], json.dumps(row["required_fields"])),
            )
    conn.close()


# ---------- categories ----------

def list_categories():
    conn = connect()
    rows = conn.execute("SELECT * FROM categories ORDER BY id").fetchall()
    conn.close()
    return [
        {"id": r["id"], "name": r["name"], "domain": r["domain"], "authority": r["authority"],
         "required_fields": json.loads(r["required_fields"])}
        for r in rows
    ]


def get_category(name):
    """Look a category up by name, case-insensitively. Returns None if there is no such category."""
    if not name:
        return None
    conn = connect()
    row = conn.execute("SELECT * FROM categories WHERE lower(name) = lower(?)", (name.strip(),)).fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row["id"], "name": row["name"], "domain": row["domain"],
            "authority": row["authority"], "required_fields": json.loads(row["required_fields"])}


def create_category(name, domain, authority, required_fields):
    conn = connect()
    with conn:
        cur = conn.execute(
            "INSERT INTO categories (name, domain, authority, required_fields) VALUES (?,?,?,?)",
            (name, domain, authority, json.dumps(required_fields or [])),
        )
        new_id = cur.lastrowid
    conn.close()
    return {"id": new_id, "name": name, "domain": domain, "authority": authority,
            "required_fields": required_fields or []}


# ---------- shaping ----------

def _complaint(row):
    """One complaints row -> the public `Complaint` shape from section 6 of the brief."""
    count, severity = row["report_count"], row["severity"]
    return {
        "id": row["id"], "domain": row["domain"], "category": row["category"],
        "authority": row["authority"], "building": row["building"], "spot": row["spot"],
        "meal": row["meal"], "summary": row["summary"], "severity": severity,
        "status": row["status"], "escalated": bool(row["escalated"]),
        "needs_details": bool(row["needs_details"]), "report_count": count,
        "priority": cats.priority(count, severity),
        "photo_count": row["photo_count"] if "photo_count" in row.keys() else 0,
        "first_reported_at": row["first_reported_at"], "last_reported_at": row["last_reported_at"],
        "resolution_note": row["resolution_note"], "suggested_category": row["suggested_category"],
    }


_SELECT = """
SELECT c.*, (SELECT COUNT(*) FROM reports r WHERE r.complaint_id = c.id AND r.photo_path IS NOT NULL
             AND r.photo_path != '') AS photo_count
FROM complaints c
"""


# ---------- what P1's tools call ----------

def find_open(category, building=None, limit=5):
    """Up to `limit` open complaints in a category (and building, if given), busiest first."""
    sql = _SELECT + " WHERE c.status != 'resolved' AND lower(c.category) = lower(?)"
    params = [category or ""]
    if building:
        sql += " AND (c.building = ? OR c.building IS NULL)"
        params.append(building)
    sql += " ORDER BY c.report_count DESC, c.last_reported_at DESC LIMIT ?"
    params.append(limit)
    conn = connect()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [_complaint(r) for r in rows]


def create_complaint(fields):
    """Create a complaint plus its first report. `fields` may carry a `report` dict."""
    report = fields.get("report") or {}
    category = get_category(fields.get("category")) or get_category("Other")
    when = report.get("created_at") or now_iso()
    severity = fields.get("severity") or "medium"
    building = fields.get("building") or None
    if category["domain"] == "Mess":
        building = building or cats.DEFAULT_MESS

    conn = connect()
    with conn:
        cur = conn.execute(
            """INSERT INTO complaints (category, domain, authority, building, spot, meal, summary, details,
               severity, status, escalated, needs_details, report_count, suggested_category,
               first_reported_at, last_reported_at, resolved_at, resolution_note)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (category["name"], category["domain"], category["authority"], building,
             fields.get("spot") or None, fields.get("meal") or None,
             fields.get("summary") or "(no summary)", fields.get("details") or None,
             severity, fields.get("status") or "open",
             int(cats.is_escalated(1, severity)), int(bool(fields.get("needs_details"))), 1,
             fields.get("suggested_category") or None, when, when,
             fields.get("resolved_at"), fields.get("resolution_note")),
        )
        complaint_id = cur.lastrowid
        _insert_report(conn, complaint_id, {**report, "outcome": report.get("outcome") or "filed",
                                            "created_at": when})
    conn.close()
    return get_complaint(complaint_id)


def _insert_report(conn, complaint_id, report):
    return conn.execute(
        """INSERT INTO reports (complaint_id, thread_id, raw_text, language, photo_path, outcome,
           merge_reason, followups, created_at) VALUES (?,?,?,?,?,?,?,?,?)""",
        (complaint_id, report.get("thread_id"), report.get("raw_text") or "",
         report.get("language"), report.get("photo_path"), report.get("outcome"),
         report.get("merge_reason"), json.dumps(report.get("followups") or []),
         report.get("created_at") or now_iso()),
    ).lastrowid


def add_report(complaint_id, report):
    """Add a report to an existing complaint: bump the count, keep the highest severity seen."""
    conn = connect()
    row = conn.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    if not row:
        conn.close()
        raise ValueError(f"there is no complaint #{complaint_id}")
    when = report.get("created_at") or now_iso()
    new_sev = report.get("severity")
    severity = row["severity"]
    if new_sev in cats.SEVERITY_WEIGHT and cats.SEVERITY_WEIGHT[new_sev] > cats.SEVERITY_WEIGHT.get(severity, 0):
        severity = new_sev  # a photo can raise severity; it never lowers it
    count = row["report_count"] + 1
    with conn:
        _insert_report(conn, complaint_id, {**report, "outcome": report.get("outcome") or "merged",
                                            "created_at": when})
        conn.execute(
            "UPDATE complaints SET report_count=?, severity=?, escalated=?, last_reported_at=? WHERE id=?",
            (count, severity, int(cats.is_escalated(count, severity)), when, complaint_id),
        )
    conn.close()
    return get_complaint(complaint_id)


def create_report(report):
    """A report with no complaint behind it: a rejection, or a thread still being asked about."""
    conn = connect()
    with conn:
        report_id = _insert_report(conn, None, report)
    conn.close()
    return {"id": report_id, **report}


# ---------- what the API serves ----------

def get_complaint(complaint_id):
    conn = connect()
    row = conn.execute(_SELECT + " WHERE c.id = ?", (complaint_id,)).fetchone()
    conn.close()
    return _complaint(row) if row else None


def get_complaint_detail(complaint_id):
    """Complaint + the authority-only report list."""
    complaint = get_complaint(complaint_id)
    if not complaint:
        return None
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM reports WHERE complaint_id = ? ORDER BY created_at, id", (complaint_id,)
    ).fetchall()
    conn.close()
    complaint["reports"] = [
        {"id": r["id"], "raw_text": r["raw_text"],
         "photo_url": f"/uploads/{Path(r['photo_path']).name}" if r["photo_path"] else None,
         "created_at": r["created_at"], "merge_reason": r["merge_reason"],
         "followups": json.loads(r["followups"] or "[]")}
        for r in rows
    ]
    return complaint


def list_complaints(domain=None, authority=None, status=None, sort="priority"):
    sql, params = _SELECT + " WHERE 1=1", []
    for column, value in (("domain", domain), ("authority", authority), ("status", status)):
        if value:
            sql += f" AND c.{column} = ?"
            params.append(value)
    conn = connect()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    out = [_complaint(r) for r in rows]
    if sort == "recent":
        out.sort(key=lambda c: c["last_reported_at"] or "", reverse=True)
    else:
        out.sort(key=lambda c: (c["escalated"], c["priority"], c["last_reported_at"] or ""), reverse=True)
    return out


def update_status(complaint_id, status, note=None):
    if status not in cats.STATUSES:
        raise ValueError(f"status must be one of {cats.STATUSES}")
    conn = connect()
    with conn:
        conn.execute(
            "UPDATE complaints SET status=?, resolution_note=COALESCE(?, resolution_note), "
            "resolved_at=CASE WHEN ?='resolved' THEN ? ELSE NULL END WHERE id=?",
            (status, note, status, now_iso(), complaint_id),
        )
    conn.close()
    return get_complaint(complaint_id)


def stats(domain=None):
    conn = connect()
    where, params = ("WHERE domain = ?", [domain]) if domain else ("", [])
    q = lambda sql, p=None: conn.execute(sql, params if p is None else p).fetchall()

    counts = {r["status"]: r["n"] for r in q(f"SELECT status, COUNT(*) n FROM complaints {where} GROUP BY status")}
    today = datetime.now(IST)
    week_ago = (today - timedelta(days=7)).replace(microsecond=0).isoformat()

    rep_where = "WHERE r.complaint_id IS NOT NULL" + (" AND c.domain = ?" if domain else "")
    reported_7d = q(f"SELECT COUNT(*) n FROM reports r JOIN complaints c ON c.id=r.complaint_id "
                    f"{rep_where} AND r.created_at >= ?", params + [week_ago])[0]["n"]
    resolved_7d = q(f"SELECT COUNT(*) n FROM complaints {where or 'WHERE 1=1'} "
                    f"AND resolved_at >= ?" if where else
                    "SELECT COUNT(*) n FROM complaints WHERE resolved_at >= ?", params + [week_ago])[0]["n"]
    escalated = q(f"SELECT COUNT(*) n FROM complaints {where or 'WHERE 1=1'} AND escalated=1 AND status!='resolved'"
                  if where else
                  "SELECT COUNT(*) n FROM complaints WHERE escalated=1 AND status!='resolved'")[0]["n"]

    by_domain = [
        {"domain": r["domain"], "open": r["o"], "in_progress": r["p"], "resolved": r["d"]}
        for r in q("SELECT domain, SUM(status='open') o, SUM(status='in_progress') p, "
                   "SUM(status='resolved') d FROM complaints GROUP BY domain ORDER BY domain", [])
    ]

    top = [c for c in list_complaints(domain=domain) if c["status"] != "resolved"][:8]
    top_issues = [{"id": c["id"], "summary": c["summary"], "domain": c["domain"],
                   "priority": c["priority"], "report_count": c["report_count"],
                   "severity": c["severity"], "status": c["status"]} for c in top]

    daily_rows = {r["d"]: r["n"] for r in q(
        f"SELECT substr(r.created_at,1,10) d, COUNT(*) n FROM reports r "
        f"JOIN complaints c ON c.id=r.complaint_id {rep_where} GROUP BY d", params)}
    daily = []
    for back in range(13, -1, -1):
        day = (today - timedelta(days=back)).strftime("%Y-%m-%d")
        daily.append({"date": day, "reports": daily_rows.get(day, 0)})

    other_suggestions = [
        {"name": r["suggested_category"], "count": r["n"]}
        for r in q("SELECT suggested_category, COUNT(*) n FROM complaints WHERE category='Other' "
                   "AND suggested_category IS NOT NULL GROUP BY suggested_category ORDER BY n DESC", [])
    ]
    conn.close()
    return {
        "kpis": {"open": counts.get("open", 0), "reported_7d": reported_7d,
                 "resolved_7d": resolved_7d, "escalated": escalated},
        "by_domain": by_domain, "top_issues": top_issues, "daily": daily,
        "other_suggestions": other_suggestions,
    }
