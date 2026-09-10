# YouTube Video Summarizer — Design

## Purpose

Personal desktop tool: paste a YouTube URL, get a structured summary of the
video's content without watching it. Primarily targets lecture/educational
content. Single user, local-only, no sharing or packaging concerns.

## Scope (v1)

Core loop only: paste URL → fetch transcript → summarize via Claude →
display → auto-save to local history. No export, no search, no clipboard
button, no frame/OCR-based code capture — all deferred until the core loop
proves useful.

## Stack

- Python 3
- GUI: CustomTkinter (single desktop window, no browser/server involved)
- Transcript source: `youtube-transcript-api` (pulls existing YouTube
  captions — auto-generated or manual). No audio download/transcription
  fallback in v1; if a video has no captions, the app reports that and
  stops.
- Summarization: Anthropic Claude API
- Storage: local SQLite file via stdlib `sqlite3`

## Architecture

Single Python process, four modules + entrypoint:

- `main.py` — builds the CustomTkinter window; wires the Summarize button
  to a background thread so network calls don't freeze the UI; pushes
  results back to the main thread via `.after()`.
- `transcript.py` — extracts the video ID from a pasted URL (regex covering
  `youtu.be/...`, `watch?v=...`, `embed/...` forms) and fetches captions.
- `summarizer.py` — sends the transcript text to Claude with a prompt
  requesting: a TL;DR, a topic outline, and best-effort code snippets when
  the presenter narrates code clearly enough to reconstruct. No
  frame-extraction or OCR — the model only sees what's said aloud, not
  what's shown on screen. This is a known, accepted limitation of v1.
- `storage.py` — thin SQLite wrapper. Single table:
  `summaries(id, video_id, url, title, transcript, summary, created_at)`.

## Data Flow

1. User pastes URL, clicks Summarize.
2. `transcript.py` extracts video ID from the URL.
3. Fetch captions. On failure (no captions available, invalid URL), show an
   inline error in the UI and stop — no retries, no fallback transcription.
4. On success, send transcript to Claude via `summarizer.py`.
5. Display returned summary in the main result pane.
6. Auto-save the record (url, transcript, summary, timestamp) to SQLite.
7. History list (opened via a "History" button) refreshes to include the
   new entry.

## UI

Single window:
- URL entry field + "Summarize" button at top.
- Result text area below, showing the current summary.
- "History" button opens a simple list (title + date); clicking an entry
  loads that past summary back into the result pane.

No sidebar, no tabs — kept to one primary view per the "single input +
result view" interaction model.

## Error Handling

Three failure points, each surfaces a plain-language message in the UI
rather than crashing the app:
- Invalid/unparseable URL.
- No captions available for the video.
- Claude API failure (network error, rate limit, etc.).

No automatic retries — this is a personal tool; the user can just click
Summarize again.

## Config

Anthropic API key is read from the `ANTHROPIC_API_KEY` environment
variable. Never stored in the app or the SQLite database.

## Testing

One small `test_transcript.py` asserting the video-ID-extraction regex
correctly handles the three common YouTube URL shapes
(`youtu.be/ID`, `watch?v=ID`, `embed/ID`). This is the only piece of
non-trivial parsing logic in the app; everything else is straightforward
I/O (API calls, SQLite reads/writes) not worth a dedicated test in v1.

## Explicitly Out of Scope (v1)

- Audio download + transcription fallback for videos without captions.
- Frame extraction / OCR for on-screen-only code.
- Export to file, search/filter over history, clipboard button.
- Multi-user support, packaging/distribution, auth.
