import re
from typing import Iterable, Set


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def load_profanity_list(path: str) -> Set[str]:
    words: Set[str] = set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    words.add(normalize_text(line))
    except FileNotFoundError:
        return set()
    return words


def build_profanity_pattern(words: Iterable[str]) -> re.Pattern:
    escaped = [re.escape(w) for w in words if w]
    if not escaped:
        return re.compile(r"^$")
    return re.compile(r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE)
