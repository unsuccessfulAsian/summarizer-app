# YouTube Summarizer

A small personal desktop app I made that fetches a YouTube video's transcript and summarizes it using Groq's free-tier Llama model.

## Features

- Paste a YouTube URL, get a summary
- Summary history stored locally (SQLite)
- API key stored securely via OS keyring (no plaintext config)

## Setup

```bash
pip install -r requirements.txt
python main.py
```

On first launch, the app will prompt for a Groq API key (get one free at [console.groq.com](https://console.groq.com)). The key is stored in your OS's credential manager via `keyring`, not in a file.

### Windows shortcut

Run `create_shortcut.ps1` to add a desktop shortcut that launches the app without a console window (via `run.bat`).

## Project structure

```
main.py          entry point (python main.py)
app/
  main.py         desktop GUI (customtkinter)
  transcript.py   YouTube transcript fetching and video ID extraction
  summarizer.py   Groq API summarization
  storage.py      SQLite storage for summary history
  apikey.py       secure API key storage via keyring
tests/
```

## Tests

```bash
pytest
```
