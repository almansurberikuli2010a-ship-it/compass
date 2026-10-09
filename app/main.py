from __future__ import annotations

import asyncio
import hashlib
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import taxonomy, vision
from .checker import LineIn, check_lines
from .store import STORE, Lesson, add_pulse, record_result, snapshot

STATIC = Path(__file__).resolve().parent.parent / "static"
MAX_BYTES, TYPES_OK = 8 * 1024 * 1024, {"image/jpeg", "image/png", "image/webp"}


async def push(L: Lesson):
    """Send a fresh dashboard snapshot to every teacher screen watching this lesson."""
    if not L.watchers:
        return
    data = snapshot(L)
    for ws in list(L.watchers):
        try:
            await ws.send_json(data)
        except Exception:
            L.watchers.discard(ws)


@asynccontextmanager
async def lifespan(_):
    async def tick():  # the "last 2 minutes" numbers change even when nobody taps
        while True:
            await asyncio.sleep(10)
            for L in list(STORE.lessons.values()):
                await push(L)
    task = asyncio.create_task(tick())
    yield
    task.cancel()


app = FastAPI(title="Compass", lifespan=lifespan)


def lesson_or_404(code: str) -> Lesson:
    L = STORE.get(code)
    if not L:
        raise HTTPException(404, "We couldn't find that class code. Check it with your teacher.")
    return L


def student(code: str, session: str) -> Lesson:
    L = lesson_or_404(code)
    if session not in L.sessions:
        raise HTTPException(401, "Please join the class again.")
    if L.ended:
        raise HTTPException(410, "This lesson has ended.")
    return L


def teacher(code: str, token: str | None) -> Lesson:
    L = lesson_or_404(code)
    if not token or not secrets.compare_digest(token, L.token):
        raise HTTPException(403, "Only the teacher can open this.")
    return L


# ---------------------------------------------------------------- teacher
class LessonIn(BaseModel):
    title: str = Field("Today's lesson", max_length=80)
    room: str = Field("Room 1", max_length=30)
    subject: str = Field("Maths", max_length=30)
    label: str = Field("Lesson 1", max_length=30)
    duration: int = Field(45, ge=5, le=180)


@app.post("/api/lessons")
def create_lesson(body: LessonIn):
    L = STORE.create(body.title, body.room, body.subject, body.label, body.duration)
    return {**L.public(), "token": L.token}


@app.get("/api/dashboard/{code}")
def dashboard(code: str, x_teacher_token: str | None = Header(None)):
    return snapshot(teacher(code, x_teacher_token))


@app.post("/api/lessons/{code}/end")
async def end_lesson(code: str, x_teacher_token: str | None = Header(None)):
    L = teacher(code, x_teacher_token)
    L.ended = True
    await push(L)
    return {"ok": True}


@app.websocket("/ws/teacher/{code}")
async def teacher_ws(ws: WebSocket, code: str, token: str = ""):
    L = STORE.get(code)
    if not L or not secrets.compare_digest(token, L.token):
        await ws.close(code=4403)
        return
    await ws.accept()
    L.watchers.add(ws)
    try:
        await ws.send_json(snapshot(L))
        while True:
            await ws.receive_text()  # keeps the connection open; the client sends nothing
    except WebSocketDisconnect:
        pass
    finally:
        L.watchers.discard(ws)


# ---------------------------------------------------------------- student
class JoinIn(BaseModel):
    code: str
    student_code: str | None = Field(None, max_length=40)


class PulseIn(BaseModel):
    code: str
    session: str
    kind: str = Field(pattern="^(lost|got_it)$")


@app.get("/api/lessons/{code}")
def lesson_info(code: str):
    return lesson_or_404(code).public()


@app.post("/api/join")
def join(body: JoinIn):
    L = lesson_or_404(body.code)
    if L.ended:
        raise HTTPException(410, "This lesson has ended.")
    sid = secrets.token_urlsafe(12)
    # The optional student code is only stored as a one-way hash and is never shown.
    h = hashlib.sha256(body.student_code.encode()).hexdigest()[:12] if body.student_code else None
    L.sessions[sid] = {"joined": 0, "code_hash": h}
    return {"session": sid, "lesson": L.public()}


@app.post("/api/pulse")
async def pulse(body: PulseIn):
    L = student(body.code, body.session)
    fresh = add_pulse(L, body.session, body.kind)
    await push(L)
    return {"ok": True, "duplicate": not fresh}


class LineModel(BaseModel):
    text: str = Field(max_length=200)
    box: list[float] | None = None
    unclear: list[dict] = []


class CheckIn(BaseModel):
    lines: list[LineModel] = Field(max_length=40)
    task_text: str | None = None
    code: str | None = None
    session: str | None = None
    result_id: str | None = None


def _run(lines, task_text=None):
    return check_lines([LineIn(l["text"], l.get("box"), l.get("unclear") or []) for l in lines], task_text)


@app.post("/api/check")
async def check(body: CheckIn):
    """Check lines you already have as text (used to re-check after a character is confirmed)."""
    res = _run([l.model_dump() for l in body.lines], body.task_text)
    res["reading_quality"], res["result_id"] = "good", body.result_id
    if body.code and body.session and body.result_id:
        L = student(body.code, body.session)
        record_result(L, body.session, res["steps"], body.result_id)
        await push(L)
    return res


async def _read(f: UploadFile) -> tuple[bytes, str]:
    if f.content_type not in TYPES_OK:
        raise HTTPException(415, "Please use a JPEG, PNG or WebP photo.")
    data = await f.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "That photo is too large (8 MB max).")
    return data, f.content_type


@app.post("/api/analyze")
async def analyze(code: str = Form(...), session: str = Form(...), photo: UploadFile = File(...),
                  task_photo: UploadFile | None = File(None)):
    L = student(code, session)
    img, media = await _read(photo)
    try:
        data = await vision.read_lines(img, media)
        task_text = await vision.read_task(*(await _read(task_photo))) if task_photo else None
    except vision.RateLimited as e:
        logging.getLogger("compass").warning("photo reader rate limit: %s", e)
        raise HTTPException(429, f"The free photo reader is busy right now. Please try again in about {e.retry_after} seconds.")
    except vision.VisionError as e:
        logging.getLogger("compass").warning("photo reader failed: %s", e)  # photos are never logged
        raise HTTPException(502, "I couldn't reach the photo reader. Nothing was shared. Try again in a moment.")
    if data["reading_quality"] == "low":
        return {"reading_quality": "low", "steps": [], "task": None, "needs_task_photo": False}
    res = _run(data["lines"], task_text)
    res["reading_quality"], res["demo"] = "good", bool(data.get("demo"))
    res["result_id"] = record_result(L, session, res["steps"])
    await push(L)
    return res


class FeedbackIn(BaseModel):
    code: str
    session: str
    step: int
    mistake_type: str | None = None


@app.post("/api/feedback")
def feedback(body: FeedbackIn):
    """'This isn't right': kept in memory so you can measure how often the checker is disputed."""
    L = student(body.code, body.session)
    L.feedback.append({"step": body.step, "type": body.mistake_type})
    return {"ok": True}


@app.get("/api/legend")
def legend():
    return taxonomy.legend()


@app.middleware("http")
async def no_cache(request, call_next):
    """Make the browser re-check pages and scripts every time, so edits show up after a reload."""
    resp = await call_next(request)
    p = request.url.path
    if p in ("/", "/teacher") or p.startswith("/static/"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


# ---------------------------------------------------------------- pages
@app.get("/")
def student_page():
    return FileResponse(STATIC / "index.html")


@app.get("/teacher")
def teacher_page():
    return FileResponse(STATIC / "teacher.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
