import io
import csv

import telebot

from config import BOT_TOKEN, DISCUSSION_CHAT_ID
from db import init_db, is_verified_user, list_verified_users
from moderation import ProfanityFilter, handle_profanity
from verification import handle_new_chat_members, handle_verify_callback
from voting import handle_vote_callback, handle_vote_trigger


if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not configured")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
profanity_filter = ProfanityFilter()


@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Бот-модератор активен.")


@bot.message_handler(commands=["export_verified"])
def export_verified(message):
    if message.chat.id != DISCUSSION_CHAT_ID:
        return
    admins = bot.get_chat_administrators(message.chat.id)
    admin_ids = {admin.user.id for admin in admins}
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "Команда доступна только администраторам.")
        return
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["user_id", "verified_at"])
    for row in list_verified_users():
        writer.writerow([row["user_id"], row["verified_at"].isoformat()])
    output.seek(0)
    bot.send_document(
        message.chat.id,
        ("verified_users.csv", output.getvalue().encode("utf-8")),
    )


@bot.message_handler(content_types=["new_chat_members"])
def on_new_members(message):
    if message.chat.id != DISCUSSION_CHAT_ID:
        return
    handle_new_chat_members(bot, message)


@bot.message_handler(content_types=["text", "photo", "video", "document"])
def on_message(message):
    if message.chat.id != DISCUSSION_CHAT_ID:
        return
    if message.from_user and not is_verified_user(message.from_user.id):
        return
    if handle_profanity(bot, message, profanity_filter):
        return
    handle_vote_trigger(bot, message, bot.get_me().username)


@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    if handle_verify_callback(bot, call):
        return
    if handle_vote_callback(bot, call):
        return


if __name__ == "__main__":
    init_db()
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
