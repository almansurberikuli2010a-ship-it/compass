"""Lessons live in memory (restarting the server clears them; photos are never stored)."""
from __future__ import annotations

import secrets
import time
from collections import defaultdict

from . import taxonomy

WORDS = ["MAPLE", "CEDAR", "BIRCH", "ASPEN", "PINE", "ELM", "OAK", "LARCH"]
WINDOW = 120  # seconds: "last 2 minutes"


class Lesson:
    def __init__(self, title, room, subject, label, duration):
        self.code = f"{secrets.choice(WORDS)}{secrets.randbelow(10)}"
        self.token = secrets.token_urlsafe(16)
        self.title, self.room, self.subject, self.label = title, room, subject, label
        self.duration = duration
        self.started, self.ended = time.time(), False
        self.sessions: dict[str, dict] = {}       # anonymous session id -> {"joined", "last_pulse"}
        self.pulses: list[tuple[float, str, str]] = []  # (time, session, "lost" | "got_it")
        self.results: list[dict] = []
        self.feedback: list[dict] = []
        self.watchers: set = set()                # teacher WebSockets

    def minute(self, t=None):
        return int(((t or time.time()) - self.started) // 60)

    def public(self):
        return {"code": self.code, "title": self.title, "room": self.room, "subject": self.subject,
                "label": self.label, "ended": self.ended}


class Store:
    def __init__(self):
        self.lessons: dict[str, Lesson] = {}

    def create(self, *a):
        L = Lesson(*a)
        while L.code in self.lessons:
            L = Lesson(*a)
        self.lessons[L.code] = L
        return L

    def get(self, code):
        return self.lessons.get((code or "").strip().upper())


STORE = Store()


def add_pulse(L: Lesson, session: str, kind: str) -> bool:
    """False if it was a duplicate tap (same student within 2 seconds)."""
    now, s = time.time(), L.sessions[session]
    if now - s.get("last_pulse", 0) < 2:
        return False
    s["last_pulse"] = now
    L.pulses.append((now, session, kind))
    return True


def record_result(L: Lesson, session: str, steps: list[dict], result_id: str | None = None) -> str:
    types = [s["mistake"]["type"] for s in steps if s["mistake"]]
    types += ["unclear_char" for s in steps if s["status"] == "unreadable"]
    entry = {"id": result_id or secrets.token_urlsafe(6), "t": time.time(), "session": session,
             "types": types, "steps": [{"index": s["index"], "type": s["mistake"]["type"] if s["mistake"] else None,
                                        "status": s["status"], "certainty": s["mistake"]["certainty"] if s["mistake"] else None}
                                       for s in steps]}
    for i, old in enumerate(L.results):  # a re-check replaces the earlier entry, keeping its time
        if old["id"] == entry["id"] and old["session"] == session:
            entry["t"] = old["t"]
            L.results[i] = entry
            return entry["id"]
    L.results.append(entry)
    return entry["id"]


def _label(r):
    steps = [s for s in r["steps"] if s["type"]]
    if steps:
        return ("Hint available", "hint") if steps[0]["certainty"] == "certain" else ("Worth checking", "check")
    if any(s["status"] == "unreadable" for s in r["steps"]):
        return "Confirm character", "check"
    return "Checked", "ok"


def _summary(r, L):
    steps = [s for s in r["steps"] if s["type"]]
    if steps:
        return f"{taxonomy.name(steps[0]['type'])} · step {steps[0]['index']}"
    unread = [s for s in r["steps"] if s["status"] == "unreadable"]
    return "Unreadable character" if unread else "Steps follow through"


def _type(r):
    steps = [s for s in r["steps"] if s["type"]]
    return steps[0]["type"] if steps else ("unclear_char" if any(s["status"] == "unreadable" for s in r["steps"]) else None)


def snapshot(L: Lesson, now: float | None = None) -> dict:
    now = now or time.time()
    total = len(L.sessions)
    latest = {}
    for t, s, k in L.pulses:  # pulses are appended in time order, so the last one wins
        if now - t <= WINDOW:
            latest[s] = k
    lost = sum(1 for k in latest.values() if k == "lost")
    got = sum(1 for k in latest.values() if k == "got_it")

    # "Where the pace changed": distinct students who felt lost in each 2-minute window
    n_win = int((now - L.started) // WINDOW) + 1
    seen = [set() for _ in range(n_win)]
    for t, s, k in L.pulses:
        w = int((t - L.started) // WINDOW)
        if k == "lost" and 0 <= w < n_win:
            seen[w].add(s)
    windows = [{"minute": i * 2, "lost": len(x)} for i, x in enumerate(seen)]
    peak = max(windows, key=lambda w: w["lost"]) if any(w["lost"] for w in windows) else None

    # Heatmap: distinct students per mistake row, in 5-minute bins
    cur = L.minute(now) // 5
    first = max(0, cur - 5)
    bins = list(range(first, cur + 1))
    cells = defaultdict(lambda: defaultdict(set))
    rep = {}  # the mistake type whose symbol represents each heatmap row
    for r in L.results:
        b = L.minute(r["t"]) // 5
        for ty in set(r["types"]):
            cells[taxonomy.row(ty)][b].add(r["session"])
            rep.setdefault(taxonomy.row(ty), ty)
    rows = [{"label": lab, "type": rep[lab], "cells": [len(c[b]) for b in bins]} for lab, c in cells.items()
            if any(c[b] for b in bins)]
    rows.sort(key=lambda x: -sum(x["cells"]))

    # Insight: what went wrong in the 5 minutes around the confusion peak?
    insight, top_type = None, None
    if peak and peak["lost"] >= 2:
        lo, hi = peak["minute"] - 1, peak["minute"] + 3
        by_type = defaultdict(set)
        for r in L.results:
            if lo <= L.minute(r["t"]) <= hi:
                for ty in set(r["types"]):
                    if ty != "unclear_char":
                        by_type[ty].add(r["session"])
        if by_type:
            top_type = max(by_type, key=lambda k: len(by_type[k]))
            n = len(by_type[top_type])
            insight = {"headline": f"Confusion peaked at minute {peak['minute']}; {n} of {total} then made {taxonomy.plural(top_type)}",
                       "body": "A shared pattern, not a judgment. Revisit it before moving on.",
                       "based_on": f"minutes {max(lo, 0)}–{hi}"}

    unread = sum(1 for r in L.results if any(s["status"] == "unreadable" for s in r["steps"]))
    latest_work = []
    for r in reversed(L.results[-8:]):
        label, tone = _label(r)
        secs = int(r["t"] - L.started)
        latest_work.append({"type": _type(r), "clock": f"{secs // 60:02d}:{secs % 60:02d}", "summary": _summary(r, L), "label": label, "tone": tone})
    return {
        "lesson": {**L.public(), "minute": L.minute(now), "duration": L.duration},
        "students": total,
        "room": {"lost": lost, "got_it": got, "quiet": max(total - lost - got, 0)},
        "timeline": {"windows": windows, "peak": peak},
        "heatmap": {"bins": [f"{b * 5}–{b * 5 + 4} min" for b in bins], "rows": rows},
        "insight": insight,
        "plan": taxonomy.plan(top_type or "check"),
        "work": {"photos": len(L.results), "checked": len(L.results) - unread, "clarify": unread, "latest": latest_work},
    }
