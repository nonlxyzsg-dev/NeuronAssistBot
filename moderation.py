from telebot.types import Message

from config import PROFANITY_WORDS_PATH
from db import log_action
from utils import contains_profanity, load_profanity_words


class ProfanityFilter:
    def __init__(self, words_path: str = PROFANITY_WORDS_PATH):
        self.words_path = words_path
        self.profanity_words = load_profanity_words(words_path)

    def refresh(self):
        self.profanity_words = load_profanity_words(self.words_path)

    def message_contains_profanity(self, message: Message) -> bool:
        text = message.text or message.caption or ""
        return contains_profanity(text, self.profanity_words)



def handle_profanity(bot, message: Message, profanity_filter: ProfanityFilter):
    if not profanity_filter.message_contains_profanity(message):
        return False
    bot.delete_message(message.chat.id, message.message_id)
    log_action(
        "profanity_deleted",
        message.from_user.id if message.from_user else None,
        message.message_id,
        message.chat.id,
        "Profanity filter matched",
    )
    return True
