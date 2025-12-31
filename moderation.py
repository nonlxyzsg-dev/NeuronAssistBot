from typing import TYPE_CHECKING

try:  # pragma: no cover - fallback for environments without telebot installed
    from telebot.types import Message
except ImportError:  # pragma: no cover
    class Message:  # type: ignore
        chat = None
        message_id: int
        text: str | None
        caption: str | None
        from_user = None

from db import log_action
from utils import normalize_text, build_profanity_pattern, load_profanity_list

PROFANITY_WORDS_PATH = "profanity_words.txt"


class ProfanityFilter:
    def __init__(self, words_path: str = PROFANITY_WORDS_PATH):
        words = load_profanity_list(words_path)
        self.pattern = build_profanity_pattern(words)

    def is_profane(self, text: str) -> bool:
        if not text:
            return False
        normalized = normalize_text(text)
        return bool(self.pattern.search(normalized))


def moderate_message(bot, message: Message, profanity_filter: ProfanityFilter):
    text = message.text or message.caption
    if not text:
        return
    if profanity_filter.is_profane(text):
        bot.delete_message(message.chat.id, message.message_id)
        log_action(message.from_user.id, "deleted_profane", message.message_id, text)
