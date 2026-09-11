import keyring

_SERVICE = "youtube-summarizer"
_KEY = "GROQ_API_KEY"


def get_api_key() -> str | None:
    return keyring.get_password(_SERVICE, _KEY)


def set_api_key(key: str) -> None:
    keyring.set_password(_SERVICE, _KEY, key)
