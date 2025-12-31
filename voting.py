import threading
from datetime import datetime
from telebot import TeleBot
from telebot.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message

from config import Settings
from db import add_vote, close_vote, count_spam_votes, get_or_create_vote, get_open_votes_older_than, is_user_verified, log_action


class VoteManager:
    def __init__(self, bot: TeleBot, settings: Settings):
        self.bot = bot
        self.settings = settings

    def _build_markup(self, vote_id: int) -> InlineKeyboardMarkup:
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🚫 Спам", callback_data=f"vote:{vote_id}:spam"),
            InlineKeyboardButton("✅ Не спам", callback_data=f"vote:{vote_id}:ok"),
        )
        return markup

    def start_vote(self, message: Message, replied: Message):
        vote_id = get_or_create_vote(message.chat.id, replied.message_id)
        markup = self._build_markup(vote_id)
        self.bot.reply_to(
            message,
            f"Голосование о спаме для сообщения {replied.from_user.first_name}",
            reply_markup=markup,
        )
        log_action(message.from_user.id, "vote_started", replied.message_id)
        timer = threading.Timer(self.settings.vote_ttl_seconds, self._expire_vote, args=[vote_id, replied])
        timer.daemon = True
        timer.start()

    def handle_vote(self, call: CallbackQuery):
        data = call.data or ""
        if not data.startswith("vote:"):
            return
        _, vote_id_str, vote_type = data.split(":", 2)
        vote_id = int(vote_id_str)
        is_spam = vote_type == "spam"
        if not is_user_verified(call.from_user.id):
            self.bot.answer_callback_query(call.id, "Только верифицированные пользователи могут голосовать")
            return
        inserted = add_vote(vote_id, call.from_user.id, is_spam)
        if not inserted:
            self.bot.answer_callback_query(call.id, "Голос уже учтен")
            return
        self.bot.answer_callback_query(call.id, "Голос учтен")
        spam_votes = count_spam_votes(vote_id)
        if spam_votes >= self.settings.spam_threshold:
            self._finalize_vote(vote_id, call.message, "Порог спам голосов достигнут", delete_target=True)

    def _finalize_vote(self, vote_id: int, vote_message: Message, reason: str, delete_target: bool = False):
        if delete_target and vote_message.reply_to_message:
            self.bot.delete_message(vote_message.chat.id, vote_message.reply_to_message.message_id)
        close_vote(vote_id, reason)
        new_text = f"Голосование закрыто: {reason}"
        try:
            self.bot.edit_message_text(new_text, chat_id=vote_message.chat.id, message_id=vote_message.message_id)
        except Exception:
            # message might be already edited or deleted
            pass
        if vote_message.reply_to_message:
            log_action(
                vote_message.reply_to_message.from_user.id,
                "vote_result",
                vote_message.reply_to_message.message_id,
                reason,
            )

    def _expire_vote(self, vote_id: int, vote_message: Message):
        close_vote(vote_id, "Время голосования истекло")
        try:
            self.bot.edit_message_text(
                "Голосование закрыто: время истекло",
                chat_id=vote_message.chat.id,
                message_id=vote_message.message_id,
            )
        except Exception:
            pass

    def close_expired_votes(self):
        expired_votes = get_open_votes_older_than(self.settings.vote_ttl_seconds)
        for vote in expired_votes:
            dummy_message = Message(
                message_id=vote["target_message_id"],
                from_user=None,
                date=datetime.utcnow(),
                chat=self.bot.get_chat(vote["target_chat_id"]),
                content_type="text",
                options={},
                json_string={},
            )
            self._expire_vote(vote["id"], dummy_message)
