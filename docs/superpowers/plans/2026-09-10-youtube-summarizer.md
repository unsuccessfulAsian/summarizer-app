# YouTube Video Summarizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a personal desktop app that takes a YouTube URL, summarizes the video via its captions and the Claude API, shows the result, and saves it to local history.

**Architecture:** Single Python process, CustomTkinter GUI. Four modules (`transcript.py`, `summarizer.py`, `storage.py`, plus `main.py` as entrypoint) each own one responsibility: URL parsing/caption fetch, Claude summarization, SQLite persistence, and UI wiring/threading.

**Tech Stack:** Python 3, `customtkinter`, `youtube-transcript-api`, `anthropic` (Claude API SDK), stdlib `sqlite3` and `urllib`.

**Spec:** `docs/superpowers/specs/2026-09-10-youtube-summarizer-design.md`

## Global Constraints

- Anthropic API key read from `ANTHROPIC_API_KEY` environment variable — never stored in code, config files, or the SQLite database.
- No audio-download/transcription fallback in v1 — if a video has no captions, surface an error and stop.
- No frame extraction/OCR for on-screen code — summaries reconstruct code only from narrated speech.
- All network calls (transcript fetch, Claude API) run off the Tkinter main thread so the UI never freezes.
- Every failure (bad URL, no captions, API error) shows a plain-language message in the UI — no crashes, no silent retries.
- Out of scope for v1: export-to-file, history search/filter, clipboard button.

---

### Task 1: Video ID extraction

**Files:**
- Create: `transcript.py`
- Test: `tests/test_transcript.py`

**Interfaces:**
- Produces: `extract_video_id(url: str) -> str | None` — returns the 11-character YouTube video ID, or `None` if the URL doesn't match a known YouTube URL shape.

- [ ] **Step 1: Write the failing test**

Create `tests/test_transcript.py`:

```python
from transcript import extract_video_id


def test_extract_video_id_watch_url():
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_short_url():
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_embed_url():
    assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_watch_url_with_extra_params():
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s") == "dQw4w9WgXcQ"


def test_extract_video_id_invalid_url():
    assert extract_video_id("https://example.com/not-youtube") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_transcript.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'transcript'`

- [ ] **Step 3: Write minimal implementation**

Create `transcript.py`:

```python
import re

_VIDEO_ID_PATTERNS = [
    re.compile(r"(?:youtu\.be/)([A-Za-z0-9_-]{11})"),
    re.compile(r"(?:youtube\.com/watch\?v=)([A-Za-z0-9_-]{11})"),
    re.compile(r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})"),
]


def extract_video_id(url: str) -> str | None:
    for pattern in _VIDEO_ID_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_transcript.py -v`
Expected: PASS (all 5 tests)

- [ ] **Step 5: Commit**

```bash
git add transcript.py tests/test_transcript.py
git commit -m "feat: add YouTube video ID extraction"
```

---

### Task 2: Transcript and title fetching

**Files:**
- Modify: `transcript.py`
- Create: `requirements.txt`

**Interfaces:**
- Consumes: nothing from earlier tasks (this task adds to `transcript.py` alongside `extract_video_id`).
- Produces:
  - `class TranscriptError(Exception)` — raised when no transcript is available or the fetch fails.
  - `fetch_transcript(video_id: str) -> str` — returns the full transcript as one plain-text string (captions joined with spaces), raises `TranscriptError` on failure.
  - `get_video_title(video_id: str) -> str` — returns the video's title via YouTube's oEmbed endpoint, falls back to `video_id` if the request fails.

- [ ] **Step 1: Create requirements.txt**

```
customtkinter
youtube-transcript-api
anthropic
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: packages install without error

- [ ] **Step 3: Add transcript and title fetching to transcript.py**

Append to `transcript.py`:

```python
import json
import urllib.request
import urllib.error

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


class TranscriptError(Exception):
    pass


def fetch_transcript(video_id: str) -> str:
    try:
        segments = YouTubeTranscriptApi.get_transcript(video_id)
    except (TranscriptsDisabled, NoTranscriptFound) as exc:
        raise TranscriptError(f"No captions available for this video: {exc}") from exc
    except Exception as exc:
        raise TranscriptError(f"Failed to fetch transcript: {exc}") from exc
    return " ".join(segment["text"] for segment in segments)


def get_video_title(video_id: str) -> str:
    oembed_url = (
        "https://www.youtube.com/oembed"
        f"?url=https://www.youtube.com/watch?v={video_id}&format=json"
    )
    try:
        with urllib.request.urlopen(oembed_url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data.get("title", video_id)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return video_id
```

- [ ] **Step 4: Manual verification**

Run: `python -c "from transcript import fetch_transcript, get_video_title; vid='dQw4w9WgXcQ'; print(get_video_title(vid)); print(fetch_transcript(vid)[:200])"`
Expected: prints the video's real title, then the first 200 characters of its transcript. If this video has no captions, substitute any YouTube video ID known to have captions (e.g. a talk or lecture).

- [ ] **Step 5: Commit**

```bash
git add transcript.py requirements.txt
git commit -m "feat: add transcript and title fetching"
```

---

### Task 3: Local storage

**Files:**
- Create: `storage.py`

**Interfaces:**
- Produces:
  - `init_db(db_path: str = "summaries.db") -> None` — creates the `summaries` table if it doesn't exist.
  - `save_summary(video_id: str, url: str, title: str, transcript: str, summary: str, db_path: str = "summaries.db") -> int` — inserts a row, returns its `id`.
  - `get_history(db_path: str = "summaries.db") -> list[dict]` — returns `[{"id": int, "title": str, "created_at": str}, ...]` ordered newest first.
  - `get_summary(summary_id: int, db_path: str = "summaries.db") -> dict | None` — returns the full row as a dict (`id`, `video_id`, `url`, `title`, `transcript`, `summary`, `created_at`), or `None` if not found.

- [ ] **Step 1: Write storage.py**

```python
import sqlite3
from datetime import datetime, timezone


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = "summaries.db") -> None:
    conn = _connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                transcript TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_summary(
    video_id: str,
    url: str,
    title: str,
    transcript: str,
    summary: str,
    db_path: str = "summaries.db",
) -> int:
    conn = _connect(db_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO summaries (video_id, url, title, transcript, summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (video_id, url, title, transcript, summary, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_history(db_path: str = "summaries.db") -> list[dict]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, title, created_at FROM summaries ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_summary(summary_id: int, db_path: str = "summaries.db") -> dict | None:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM summaries WHERE id = ?", (summary_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
```

- [ ] **Step 2: Manual verification**

Run:

```bash
python -c "
import storage
storage.init_db('test.db')
rid = storage.save_summary('abc123', 'https://youtu.be/abc123', 'Test Video', 'transcript text', 'summary text', db_path='test.db')
print('inserted id:', rid)
print(storage.get_history(db_path='test.db'))
print(storage.get_summary(rid, db_path='test.db'))
"
```

Expected: prints an inserted id of 1, a history list with one entry titled "Test Video", and the full row dict. Then delete the test artifact:

```bash
rm test.db
```

- [ ] **Step 3: Commit**

```bash
git add storage.py
git commit -m "feat: add SQLite storage for summaries"
```

---

### Task 4: Claude summarization

**Files:**
- Create: `summarizer.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (takes plain transcript text as input).
- Produces:
  - `class SummarizerError(Exception)` — raised on Claude API failures.
  - `summarize(transcript: str) -> str` — returns the summary text (TL;DR + topic outline + best-effort code snippets), raises `SummarizerError` on failure.

- [ ] **Step 1: Write summarizer.py**

```python
import anthropic

_MODEL = "claude-sonnet-5"

_PROMPT_TEMPLATE = """\
You are summarizing the transcript of a YouTube video (likely a lecture or \
educational talk). Produce a summary with this structure:

1. TL;DR — a short paragraph (3-5 sentences) capturing the video's main point.
2. Topic Outline — a bulleted, hierarchical outline of the sections/topics \
covered, with key points under each.
3. Code (if applicable) — if the speaker narrates any code clearly enough to \
reconstruct it, include it in fenced code blocks under a "Code" heading. If \
no code is discussed, omit this section entirely.

Transcript:
{transcript}
"""


class SummarizerError(Exception):
    pass


def summarize(transcript: str) -> str:
    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model=_MODEL,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": _PROMPT_TEMPLATE.format(transcript=transcript),
                }
            ],
        )
    except Exception as exc:
        raise SummarizerError(f"Claude API call failed: {exc}") from exc
    return response.content[0].text
```

- [ ] **Step 2: Manual verification**

Requires `ANTHROPIC_API_KEY` set in the environment. Run:

```bash
python -c "
from summarizer import summarize
text = 'Today we are going to talk about how sorting algorithms work. First, bubble sort compares adjacent elements and swaps them if out of order. It repeats this until the list is sorted. This is simple but slow, O(n squared) in the worst case.'
print(summarize(text))
```

Expected: prints a summary containing a TL;DR paragraph and a topic outline referencing bubble sort.

- [ ] **Step 3: Commit**

```bash
git add summarizer.py
git commit -m "feat: add Claude-based transcript summarization"
```

---

### Task 5: Desktop GUI

**Files:**
- Create: `main.py`

**Interfaces:**
- Consumes:
  - `transcript.extract_video_id(url: str) -> str | None`
  - `transcript.fetch_transcript(video_id: str) -> str` (raises `transcript.TranscriptError`)
  - `transcript.get_video_title(video_id: str) -> str`
  - `summarizer.summarize(transcript: str) -> str` (raises `summarizer.SummarizerError`)
  - `storage.init_db(db_path: str = "summaries.db") -> None`
  - `storage.save_summary(video_id, url, title, transcript, summary, db_path="summaries.db") -> int`
  - `storage.get_history(db_path: str = "summaries.db") -> list[dict]`
  - `storage.get_summary(summary_id: int, db_path: str = "summaries.db") -> dict | None`
- Produces: `class App(customtkinter.CTk)` — the application entrypoint, run via `if __name__ == "__main__"`.

- [ ] **Step 1: Write main.py**

```python
import threading
import tkinter.messagebox as messagebox

import customtkinter

import storage
import summarizer
import transcript

customtkinter.set_appearance_mode("System")


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Summarizer")
        self.geometry("700x500")

        storage.init_db()

        self.url_entry = customtkinter.CTkEntry(self, placeholder_text="Paste YouTube URL")
        self.url_entry.pack(fill="x", padx=10, pady=(10, 5))

        button_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=10)

        self.summarize_button = customtkinter.CTkButton(
            button_frame, text="Summarize", command=self.on_summarize_click
        )
        self.summarize_button.pack(side="left")

        self.history_button = customtkinter.CTkButton(
            button_frame, text="History", command=self.open_history_window
        )
        self.history_button.pack(side="left", padx=(10, 0))

        self.status_label = customtkinter.CTkLabel(self, text="")
        self.status_label.pack(fill="x", padx=10)

        self.result_box = customtkinter.CTkTextbox(self, wrap="word")
        self.result_box.pack(fill="both", expand=True, padx=10, pady=10)

    def on_summarize_click(self):
        url = self.url_entry.get().strip()
        if not url:
            return
        self.summarize_button.configure(state="disabled")
        self.status_label.configure(text="Working...")
        thread = threading.Thread(target=self._run_summarize, args=(url,), daemon=True)
        thread.start()

    def _run_summarize(self, url: str):
        video_id = transcript.extract_video_id(url)
        if video_id is None:
            self.after(0, self._on_error, "That doesn't look like a valid YouTube URL.")
            return

        try:
            transcript_text = transcript.fetch_transcript(video_id)
        except transcript.TranscriptError as exc:
            self.after(0, self._on_error, str(exc))
            return

        title = transcript.get_video_title(video_id)

        try:
            summary_text = summarizer.summarize(transcript_text)
        except summarizer.SummarizerError as exc:
            self.after(0, self._on_error, str(exc))
            return

        storage.save_summary(video_id, url, title, transcript_text, summary_text)
        self.after(0, self._on_success, summary_text)

    def _on_success(self, summary_text: str):
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", summary_text)
        self.status_label.configure(text="Done.")
        self.summarize_button.configure(state="normal")

    def _on_error(self, message: str):
        self.status_label.configure(text="")
        self.summarize_button.configure(state="normal")
        messagebox.showerror("Error", message)

    def open_history_window(self):
        history = storage.get_history()
        window = customtkinter.CTkToplevel(self)
        window.title("History")
        window.geometry("400x400")

        for entry in history:
            label_text = f"{entry['title']}  ({entry['created_at']})"
            row = customtkinter.CTkButton(
                window,
                text=label_text,
                anchor="w",
                command=lambda eid=entry["id"], win=window: self._load_history_item(eid, win),
            )
            row.pack(fill="x", padx=5, pady=2)

    def _load_history_item(self, summary_id: int, window):
        record = storage.get_summary(summary_id)
        if record is None:
            return
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", record["summary"])
        window.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
```

- [ ] **Step 2: Manual verification**

With `ANTHROPIC_API_KEY` set, run: `python main.py`

Walk through:
1. Paste a YouTube URL for a video with captions, click Summarize. Expected: status shows "Working...", button disables, then a TL;DR + outline appears and the button re-enables.
2. Click History. Expected: a window lists the summary you just created with its title and timestamp.
3. Click that history entry. Expected: the result pane shows the saved summary and the history window closes.
4. Paste an invalid (non-YouTube) URL and click Summarize. Expected: an error dialog says the URL doesn't look valid, no crash.
5. Paste a YouTube URL for a video with captions disabled and click Summarize. Expected: an error dialog reports no captions available, no crash.

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add desktop GUI wiring transcript, summarizer, and storage"
```
