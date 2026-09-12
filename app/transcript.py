import re
import json
import urllib.request
import urllib.error

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

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


class TranscriptError(Exception):
    pass


def fetch_transcript(video_id: str) -> str:
    try:
        api = YouTubeTranscriptApi()
        transcript_obj = api.fetch(video_id)
        segments = transcript_obj.to_raw_data()
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
