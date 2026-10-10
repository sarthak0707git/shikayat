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
from starlette.concurrency import run_in_threadpool

from api import db
from complaints import categories as cats
from complaints.agent import handle_answer, handle_report

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
# Both of these run the real Gemma agent. It is synchronous and takes several seconds,
# so it goes to a worker thread: on the event loop it would freeze every other request,
# including the board polling while a judge is submitting a report.

@app.post("/api/report")
async def post_report(text: str = Form(...), photo: UploadFile | None = File(None)):
    if not text.strip():
        raise HTTPException(422, "Please write what the problem is.")
    photo_path = await run_in_threadpool(_save_photo, photo)
    thread_id = "t_" + uuid.uuid4().hex[:6]
    result = await run_in_threadpool(handle_report, text, photo_path=photo_path, thread_id=thread_id)
    return JSONResponse(result)


@app.post("/api/report/{thread_id}/answer")
async def post_answer(thread_id: str, body: AnswerIn):
    if not body.answer.strip():
        raise HTTPException(422, "Please type an answer.")
    return JSONResponse(await run_in_threadpool(handle_answer, thread_id, body.answer))
