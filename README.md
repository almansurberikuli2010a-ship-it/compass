# Compass

Teachers see **when** a lesson lost the class (Class Pulse). Students see **what kind** of mistake happened in their own work (Mistake Map). One FastAPI server, two web pages, no build step.

## Run it (Mac M1)

```bash
cd compass   # needs Python 3.9+ (3.12 recommended)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # optional: put your ANTHROPIC_API_KEY in it
set -a; source .env; set +a     # loads the variables into this terminal
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- Teacher: <http://localhost:8000/teacher> → "Start a lesson" gives a class code.
- Students: `http://<your-laptop-ip>:8000` on a phone on the same Wi-Fi (find the IP in System Settings → Wi-Fi → Details).
- **Photo reader:** `export GROQ_API_KEY=...` (free tier, for testing) or `export ANTHROPIC_API_KEY=...` (paid). If both are set, Anthropic is used; force one with `COMPASS_PROVIDER=groq`. Run your own 20–30 handwriting samples through each before choosing.
- **No API key?** The app runs in **demo mode**: every photo returns the same example from your Figma screens, so you can build and demo the whole loop first.
- At a venue with bad Wi-Fi: use your phone's hotspot for the laptop and the other phones.

## How it fits together

```
phone (student page) ──┐                       ┌── teacher page (live, WebSocket)
ESP32 button ──────────┼──►  FastAPI server ───┘
                       │     ├─ checker.py   exact maths: finds the mistake and its type
                       │     ├─ vision.py    photo -> text lines (the only outside AI call)
                       │     ├─ store.py     lessons, pulses, dashboard numbers (in memory)
                       │     └─ taxonomy.py  names, teacher rows, 5-minute plans
```

### The idea in `checker.py` (the part to understand and defend)

1. Each line is compared with the line **before it** (not with the "true" solution), so one early slip does not flag everything after it.
2. If every part of the equation changed the same way (the same number added to all parts, or all parts multiplied by the same number), the step is correct.
3. If not, the checker builds the **wrong versions** a student could have produced from the previous line (sign not flipped, distribution to the first term only, a term dropped…) and sees which one equals the student's line. That match names the mistake. Because this uses exact algebra (SymPy), `certainty: "certain"` is proved, not guessed. Heuristics (units, equals sign, layout) are marked `"likely"`.
4. Lines with characters the reader is unsure of (`1 or 7`) are **not judged** until the student confirms them.

### API contract (what your UI reads)

`POST /api/analyze` (multipart: `code`, `session`, `photo`, optional `task_photo`) →

```json
{ "reading_quality": "good", "task": "Solve: 3(x - 2) = 15", "needs_task_photo": false, "answer_ok": false,
  "steps": [ { "index": 2, "text": "3x = 15 - 6", "status": "check", "line_box": [0.1, 0.38, 0.55, 0.09],
      "mistake": { "type": "sign_slip", "name": "Sign slip", "certainty": "certain",
                   "hint": "Try adding 6 to both sides to keep the balance.",
                   "practice": "3x - 6 + 6 = 15 + __", "also": [] },
      "unreadable": [] } ] }
```

`status` is `ok | check | unreadable | unchecked`. `line_box` is `[x, y, w, h]` as fractions of the photo and can be `null`; the UI then shows the lines as a list instead.

Other routes: `POST /api/lessons`, `POST /api/join`, `POST /api/pulse` (`kind`: `lost | got_it`), `POST /api/check` (check text lines, used when a student confirms a character), `POST /api/feedback` ("This isn't right"), `GET /api/dashboard/{code}` and `WS /ws/teacher/{code}?token=…`, `GET /api/legend`.

**ESP32 button:** after a phone (or your laptop) has called `/api/join`, an ESP32 only needs to `POST /api/pulse` with `{"code":"MAPLE8","session":"<id>","kind":"lost"}`. Taps from the same session within 2 seconds are ignored.

## Tests

```bash
pytest -q        # 21 tests: every mistake type, the API, security checks, the live WebSocket
```

## Privacy, as built

- Photos are processed in memory and never saved or logged. Teachers receive counts and mistake types only, never names or photos.
- Taps are anonymous to classmates. The optional student code is stored only as a one-way hash and is not shown anywhere yet.
- **Photos do go to the AI provider** you configure in `vision.py` while it reads them. Check that provider's data terms before using real students' work, and tell students and parents.

## Honest limits

- **Not tested here:** real handwriting accuracy (needs a real API key and real student photos), real phones and browsers, and the ESP32. The UI was run in a simulated browser against the live server, not on a phone.
- `line_box` positions come from the AI and can be off. Underlines are placed per line, not per term.
- Lessons live in memory: restarting the server clears them.
- Not built yet: power-rule and fraction-sum detection, the "Classes" tab, the ESP32 sketch, your custom symbols (the `badge` icon is a placeholder slot in `static/common.js`), and conceptual types (perimeter vs area, percent). For those, `needs_task_photo` asks for the task instead of guessing.
- Check the model name in `app/vision.py` (`COMPASS_MODEL`) against Anthropic's current docs.
# compass
