import re
from pathlib import Path


NON_WORD_RE = re.compile(r"[^\w\s]+", flags=re.UNICODE)
WHITESPACE_RE = re.compile(r"\s+", flags=re.UNICODE)


def normalize_text(text: str) -> str:
    lowered = text.lower()
    cleaned = NON_WORD_RE.sub(" ", lowered)
    normalized = WHITESPACE_RE.sub(" ", cleaned).strip()
    return normalized


def load_profanity_words(file_path: str) -> set[str]:
    path = Path(file_path)
    if not path.exists():
        return set()
    words = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        word = line.strip()
        if not word or word.startswith("#"):
            continue
        words.add(normalize_text(word))
    return {word for word in words if word}


def contains_profanity(text: str, profanity_words: set[str]) -> bool:
    if not text or not profanity_words:
        return False
    normalized = normalize_text(text)
    if not normalized:
        return False
    tokens = set(normalized.split())
    return any(word in tokens for word in profanity_words)
