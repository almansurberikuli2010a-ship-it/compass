import os

os.environ["COMPASS_DEMO"] = "1"  # no outside AI calls in tests

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def setup():
    c = TestClient(app)
    lesson = c.post("/api/lessons", json={"title": "Equations", "room": "Room 8", "subject": "Maths", "label": "Lesson 04"}).json()
    code, token = lesson["code"], lesson["token"]
    sessions = [c.post("/api/join", json={"code": code}).json()["session"] for _ in range(3)]
    return c, code, token, sessions


def test_full_flow():
    c, code, token, ss = setup()
    for s in ss[:2]:
        assert c.post("/api/pulse", json={"code": code, "session": s, "kind": "lost"}).json()["ok"]
    c.post("/api/pulse", json={"code": code, "session": ss[2], "kind": "got_it"})
    r = c.post("/api/analyze", data={"code": code, "session": ss[0]}, files={"photo": ("w.png", PNG, "image/png")}).json()
    assert r["demo"] and r["reading_quality"] == "good"
    assert [s["status"] for s in r["steps"]] == ["ok", "check", "ok", "check", "unreadable"]
    assert r["steps"][1]["mistake"]["type"] == "sign_slip"
    dash = c.get(f"/api/dashboard/{code}", headers={"X-Teacher-Token": token}).json()
    assert dash["students"] == 3 and dash["room"] == {"lost": 2, "got_it": 1, "quiet": 0}
    assert dash["work"]["photos"] == 1 and dash["work"]["clarify"] == 1
    assert any(row["label"] == "Sign slips" and row["type"] == "sign_slip" for row in dash["heatmap"]["rows"])
    assert dash["work"]["latest"][0]["type"]
    assert "photo" not in str(dash).lower().replace("photos", "")  # no photo data reaches the teacher


def test_confirming_a_character_rechecks_and_updates_teacher_view():
    c, code, token, ss = setup()
    r = c.post("/api/analyze", data={"code": code, "session": ss[0]}, files={"photo": ("w.png", PNG, "image/png")}).json()
    lines = [{"text": s["text"], "box": s["line_box"], "unclear": []} for s in r["steps"]]
    lines[-1]["text"] = "x = 1"
    out = c.post("/api/check", json={"lines": lines, "code": code, "session": ss[0], "result_id": r["result_id"]}).json()
    assert out["steps"][-1]["status"] == "check"
    dash = c.get(f"/api/dashboard/{code}", headers={"X-Teacher-Token": token}).json()
    assert dash["work"]["clarify"] == 0 and dash["work"]["photos"] == 1


def test_security_and_validation():
    c, code, token, ss = setup()
    assert c.get(f"/api/dashboard/{code}").status_code == 403
    assert c.get(f"/api/dashboard/{code}", headers={"X-Teacher-Token": "nope"}).status_code == 403
    assert c.post("/api/join", json={"code": "NOPE0"}).status_code == 404
    assert c.post("/api/pulse", json={"code": code, "session": "fake", "kind": "lost"}).status_code == 401
    assert c.post("/api/pulse", json={"code": code, "session": ss[0], "kind": "bored"}).status_code == 422
    bad = c.post("/api/analyze", data={"code": code, "session": ss[0]}, files={"photo": ("w.txt", b"hi", "text/plain")})
    assert bad.status_code == 415
    c.post(f"/api/lessons/{code}/end", headers={"X-Teacher-Token": token})
    assert c.post("/api/pulse", json={"code": code, "session": ss[0], "kind": "lost"}).status_code == 410


def test_duplicate_taps_are_ignored_and_websocket_pushes():
    c, code, token, ss = setup()
    with c.websocket_connect(f"/ws/teacher/{code}?token={token}") as ws:
        assert ws.receive_json()["students"] == 3
        assert c.post("/api/pulse", json={"code": code, "session": ss[0], "kind": "lost"}).json()["duplicate"] is False
        assert ws.receive_json()["room"]["lost"] == 1
        assert c.post("/api/pulse", json={"code": code, "session": ss[0], "kind": "lost"}).json()["duplicate"] is True


def test_pages_and_scripts_are_not_cached_by_the_browser():
    c = TestClient(app)
    for path in ("/", "/teacher", "/static/common.js", "/static/app.css"):
        assert c.get(path).headers["cache-control"] == "no-cache"
    assert "t_arithmetic_slip" in c.get("/static/common.js").text
