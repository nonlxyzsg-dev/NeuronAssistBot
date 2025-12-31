import csv
import io
import logging
from telebot import TeleBot
from telebot.types import Message, CallbackQuery

from config import load_settings
from db import init_db, get_verified_users
from moderation import ProfanityFilter, moderate_message
from verification import handle_new_member, handle_verification
from voting import VoteManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def create_bot():
    settings = load_settings()
    init_db()

    bot = TeleBot(settings.bot_token, parse_mode="HTML")
    profanity_filter = ProfanityFilter()
    vote_manager = VoteManager(bot, settings)
    bot_username = bot.get_me().username

    @bot.message_handler(commands=["export_verified"])
    def export_verified(message: Message):
        chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status not in ("administrator", "creator"):
            bot.reply_to(message, "Только администратор может использовать эту команду")
            return
        rows = get_verified_users()
        text_buffer = io.StringIO()
        writer = csv.writer(text_buffer)
        writer.writerow(["user_id", "verified_at"])
        for row in rows:
            writer.writerow([row["user_id"], row["verified_at"]])
        bytes_buffer = io.BytesIO(text_buffer.getvalue().encode("utf-8"))
        bytes_buffer.seek(0)
        bot.send_document(message.chat.id, bytes_buffer, visible_file_name="verified_users.csv")

    @bot.message_handler(content_types=['new_chat_members'])
    def on_new_member(message: Message):
        if message.chat.id != settings.discussion_chat_id:
            return
        handle_new_member(bot, message)

    @bot.callback_query_handler(func=lambda call: True)
    def on_callback(call: CallbackQuery):
        if call.message.chat.id != settings.discussion_chat_id:
            return
        if call.data and call.data.startswith("verify:"):
            handle_verification(bot, call)
        elif call.data and call.data.startswith("vote:"):
            vote_manager.handle_vote(call)

    @bot.message_handler(content_types=[
        'text', 'photo', 'document', 'video', 'audio', 'voice', 'animation'
    ])
    def on_message(message: Message):
        if message.chat.id != settings.discussion_chat_id:
            return
        moderate_message(bot, message, profanity_filter)
        text = message.text or message.caption or ""
        if message.reply_to_message and f"@{bot_username}" in text:
            vote_manager.start_vote(message, message.reply_to_message)

    return bot


def main():
    bot = create_bot()
    bot.infinity_polling()


if __name__ == "__main__":
    main()
