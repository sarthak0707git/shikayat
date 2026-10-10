"""The HTTP surface. Section 6 of docs/BRIEF.md is the contract; this file implements it."""

import json
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from api import db
from complaints import categories as cats

ROOT = Path(__file__).resolve().parent.parent
UPLOADS = ROOT / "uploads"
UPLOADS.mkdir(exist_ok=True)
MAX_PHOTO_BYTES = 5 * 1024 * 1024

app = FastAPI(title="Shikayat", version="0.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
                   "http://localhost:4173", "http://127.0.0.1:4173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS)), name="uploads")


@app.on_event("startup")
def startup():
    db.init_db()


class StatusPatch(BaseModel):
    status: str
    note: str | None = None


class AnswerIn(BaseModel):
    answer: str


class CategoryIn(BaseModel):
    name: str
    domain: str
    authority: str
    required_fields: list[str] = []


def _save_photo(photo: UploadFile | None) -> str | None:
    if photo is None or not photo.filename:
        return None
    if not (photo.content_type or "").startswith("image/"):
        raise HTTPException(415, "Only image files are accepted.")
    target = UPLOADS / f"{uuid.uuid4().hex}.jpg"
    size = 0
    with target.open("wb") as out:
        while chunk := photo.file.read(64 * 1024):
            size += len(chunk)
            if size > MAX_PHOTO_BYTES:
                out.close()
                target.unlink(missing_ok=True)
                raise HTTPException(413, "That photo is larger than 5 MB.")
            out.write(chunk)
    return str(target)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/categories")
def get_categories():
    return db.list_categories()


@app.post("/api/categories")
def post_category(body: CategoryIn):
    if db.get_category(body.name):
        raise HTTPException(409, f"A category called {body.name!r} already exists.")
    return db.create_category(body.name, body.domain, body.authority, body.required_fields)


@app.get("/api/complaints")
def get_complaints(domain: str | None = None, authority: str | None = None,
                   status: str | None = None, sort: str = "priority"):
    return db.list_complaints(domain=domain, authority=authority, status=status, sort=sort)


@app.get("/api/complaints/{complaint_id}")
def get_complaint(complaint_id: int):
    detail = db.get_complaint_detail(complaint_id)
    if not detail:
        raise HTTPException(404, f"There is no complaint #{complaint_id}.")
    return detail


@app.patch("/api/complaints/{complaint_id}")
def patch_complaint(complaint_id: int, body: StatusPatch):
    if body.status not in cats.STATUSES:
        raise HTTPException(422, f"status must be one of {cats.STATUSES}")
    if not db.get_complaint(complaint_id):
        raise HTTPException(404, f"There is no complaint #{complaint_id}.")
    return db.update_status(complaint_id, body.status, body.note)


@app.get("/api/stats")
def get_stats(domain: str | None = None):
    return db.stats(domain=domain)


# ---------- reporting ----------
# P1 wires the real Gemma agent in here. Until then these return a believable
# ReportResult so the Report page can be built against the real URL from minute one.

def _mock_result(text, thread_id):
    """Shape-accurate stand-in. Deterministic on the text so the UI can be exercised."""
    low = text.lower()
    if "moon" in low or "test" in low:
        return {"thread_id": thread_id, "status": "rejected",
                "message": "This does not look like a campus issue, so we have not filed it.",
                "question": None, "complaint": None,
                "steps": [{"kind": "tool_call", "label": "Checking whether this is a campus issue"}]}
    if "ac" in low.split() or "paani tapak" in low:
        return {"thread_id": thread_id, "status": "needs_input",
                "message": "Gemma needs one more detail.",
                "question": "Kaunsa hostel aur room number?", "complaint": None,
                "steps": [{"kind": "tool_call", "label": "Looking for similar reports"},
                          {"kind": "tool_call", "label": "Asking the student for the missing details"}]}
    top = db.stats()["top_issues"]
    complaint = db.get_complaint(top[0]["id"]) if top else None
    return {"thread_id": thread_id, "status": "merged",
            "message": f"Added to #{complaint['id']}. You're the {complaint['report_count']}th student to report this."
                       if complaint else "Filed.",
            "question": None, "complaint": complaint,
            "steps": [{"kind": "tool_call", "label": "Looking for similar reports"},
                      {"kind": "tool_call", "label": "Merging into an existing complaint"}]}


@app.post("/api/report")
async def post_report(text: str = Form(...), photo: UploadFile | None = File(None)):
    if not text.strip():
        raise HTTPException(422, "Please write what the problem is.")
    photo_path = _save_photo(photo)
    thread_id = "t_" + uuid.uuid4().hex[:6]
    try:
        from complaints.agent import handle_report
    except ImportError:
        return JSONResponse(_mock_result(text, thread_id))
    return JSONResponse(handle_report(text, photo_path=photo_path, thread_id=thread_id))


@app.post("/api/report/{thread_id}/answer")
async def post_answer(thread_id: str, body: AnswerIn):
    if not body.answer.strip():
        raise HTTPException(422, "Please type an answer.")
    try:
        from complaints.agent import handle_answer
    except ImportError:
        result = _mock_result("filed after answer", thread_id)
        result["status"] = "filed"
        result["message"] = "Filed as a new complaint in the Hostel Office queue."
        return JSONResponse(result)
    return JSONResponse(handle_answer(thread_id, body.answer))
