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
            max_tokens=16000,
            messages=[
                {
                    "role": "user",
                    "content": _PROMPT_TEMPLATE.format(transcript=transcript),
                }
            ],
        )
        return next(block.text for block in response.content if block.type == "text")
    except Exception as exc:
        raise SummarizerError(f"Claude API call failed: {exc}") from exc
