"""Photo -> lines of text. This is the ONLY place an outside AI service is used.

Set GROQ_API_KEY (free tier) or ANTHROPIC_API_KEY (paid) to use it. Without a key the app runs in DEMO mode with a fixed
example, so you can build and test the UI first. Check the model name in Anthropic's docs
and override it with COMPASS_MODEL if needed. Photos are processed in memory, never saved.
"""
from __future__ import annotations

import base64
import json
import os
import re

MODEL = os.getenv("COMPASS_MODEL", "claude-sonnet-5-5")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
# Groq's free tier counts the answer length you ASK for against its tokens-per-minute budget, so keep it small.
GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "1200"))
# Provider: set COMPASS_PROVIDER=groq|anthropic, or just set one key (Anthropic wins if both are set).
PROVIDER = os.getenv("COMPASS_PROVIDER") or ("anthropic" if os.getenv("ANTHROPIC_API_KEY") or not os.getenv("GROQ_API_KEY") else "groq")
DEMO = os.getenv("COMPASS_DEMO") == "1" or not os.getenv("GROQ_API_KEY" if PROVIDER == "groq" else "ANTHROPIC_API_KEY")
_TRANSPORT = None  # tests replace this with a fake HTTP transport

LINES_PROMPT = """You read a student's handwritten maths work. Transcribe it exactly. Do NOT fix the student's mistakes.
Return ONLY JSON: {"reading_quality": "good" | "low", "lines": [{"text": "...", "box": [x, y, w, h], "unclear": [{"pos": 0, "alternatives": ["1", "7"]}]}]}
Rules:
- One entry per written line, top to bottom. Plain notation: * multiply, / divide, ^ power, x is the variable.
- box = the line's bounding box as fractions (0-1) of the image width and height.
- unclear = characters you cannot tell apart (for example 1 or 7). pos = 0-based index in text. Leave [] if sure.
- reading_quality "low" if the writing is too faint, blurry or cut off to transcribe reliably."""

TASK_PROMPT = 'Transcribe the maths task in this photo as plain text. Return ONLY JSON: {"text": "..."}'


class VisionError(Exception):
    pass


class RateLimited(VisionError):
    def __init__(self, msg, retry_after=30):
        super().__init__(msg)
        self.retry_after = retry_after


def _demo():
    rows = ["Solve: 3(x - 2) = 15", "3x - 6 = 15", "3x = 15 - 6", "3x = 9", "x = 9 - 3", "x = 7"]
    lines = [{"text": t, "box": [0.1, 0.12 + i * 0.13, 0.55, 0.09], "unclear": []} for i, t in enumerate(rows)]
    lines[-1]["unclear"] = [{"pos": 4, "alternatives": ["1", "7"]}]
    return {"reading_quality": "good", "lines": lines, "demo": True}


async def _ask_anthropic(image: bytes, media: str, prompt: str) -> str:
    from anthropic import AsyncAnthropic  # imported late so demo mode needs no key

    msg = await AsyncAnthropic().messages.create(
        model=MODEL, max_tokens=1500,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media,
                                         "data": base64.b64encode(image).decode()}},
            {"type": "text", "text": prompt}]}])
    return "".join(b.text for b in msg.content if b.type == "text")


async def _ask_groq(image: bytes, media: str, prompt: str) -> str:
    import httpx  # Groq speaks the OpenAI chat format, so plain HTTP is enough

    payload = {"model": GROQ_MODEL, "temperature": 0, "max_tokens": GROQ_MAX_TOKENS, "messages": [{"role": "user", "content": [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:{media};base64,{base64.b64encode(image).decode()}"}}]}]}
    # Qwen 3.8 27B accepts reasoning_effort "none" (thinking off): faster, and no tokens wasted on thinking.
    effort = os.getenv("GROQ_REASONING_EFFORT") or ("none" if GROQ_MODEL.startswith("qwen/qwen3.8") else "")
    if effort:
        payload["reasoning_effort"] = effort
    async with httpx.AsyncClient(timeout=90, transport=_TRANSPORT) as c:
        r = await c.post("https://api.groq.com/openai/v1/chat/completions", json=payload,
                         headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"})
    if r.status_code == 429:
        wait = int(float(r.headers.get("retry-after", 30)))
        raise RateLimited(f"Groq 429 (retry after {wait}s): {r.text[:300]}", wait)
    if r.status_code >= 400:  # keep the provider's reason (wrong model, rate limit, image too large...)
        raise VisionError(f"Groq {r.status_code}: {r.text[:300]}")
    choice = r.json()["choices"][0]
    if choice.get("finish_reason") == "length":  # a 'thinking' model can use up the whole answer budget
        raise VisionError("Groq stopped at the token limit before finishing. Try a larger GROQ_MAX_TOKENS")
    return choice["message"].get("content") or ""


async def _ask(image: bytes, media: str, prompt: str) -> dict:
    try:
        text = await (_ask_groq if PROVIDER == "groq" else _ask_anthropic)(image, media, prompt)
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)  # drop visible 'thinking' if the model prints it
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise VisionError(f"no JSON in the reply: {text[:200]!r}")
        return json.loads(m.group(0))
    except VisionError:
        raise
    except Exception as e:  # network, key, parsing
        raise VisionError(f"{type(e).__name__}: {e}") from e


def _clean(data: dict) -> dict:
    out = []
    for ln in data.get("lines", []):
        text = str(ln.get("text", "")).strip()
        if not text:
            continue
        box = ln.get("box")
        box = [min(max(float(v), 0), 1) for v in box] if isinstance(box, list) and len(box) == 4 else None
        unclear = [{"pos": int(u["pos"]), "alternatives": [str(a)[:1] for a in u["alternatives"]][:4]}
                   for u in ln.get("unclear", []) if isinstance(u.get("pos"), int)
                   and 0 <= u["pos"] < len(text) and len(u.get("alternatives", [])) >= 2]
        out.append({"text": text, "box": box, "unclear": unclear})
    return {"reading_quality": "low" if data.get("reading_quality") == "low" or not out else "good", "lines": out}


async def read_lines(image: bytes, media: str) -> dict:
    return _demo() if DEMO else _clean(await _ask(image, media, LINES_PROMPT))


async def read_task(image: bytes, media: str) -> str:
    if DEMO:
        return "Solve: 3(x - 2) = 15"
    return str((await _ask(image, media, TASK_PROMPT)).get("text", ""))
