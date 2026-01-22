from datetime import datetime, timedelta, timezone

from telebot import types
from telebot.types import CallbackQuery, Message

from config import SPAM_THRESHOLD, VOTE_TTL_SECONDS
from db import (
    add_spam_vote,
    close_spam_vote,
    count_spam_votes,
    create_spam_vote,
    get_spam_vote,
    get_spam_vote_by_target,
    is_verified_user,
    list_open_spam_votes,
    log_action,
)


VOTE_PREFIX = "vote:"


def is_vote_expired(created_at: datetime) -> bool:
    expires_at = created_at + timedelta(seconds=VOTE_TTL_SECONDS)
    return datetime.now(timezone.utc) >= expires_at



def build_vote_keyboard(vote_id: int) -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(
            text="🚫 Спам",
            callback_data=f"{VOTE_PREFIX}{vote_id}:spam",
        ),
        types.InlineKeyboardButton(
            text="✅ Не спам",
            callback_data=f"{VOTE_PREFIX}{vote_id}:ham",
        ),
    )
    return keyboard


def create_vote(bot, message: Message) -> int | None:
    target_message = message.reply_to_message
    if not target_message:
        return None
    existing = get_spam_vote_by_target(message.chat.id, target_message.message_id)
    if existing:
        return existing["vote_id"]
    vote_message = bot.send_message(
        message.chat.id,
        "Голосование: это спам?",
        reply_to_message_id=target_message.message_id,
    )
    vote_id = create_spam_vote(
        message.chat.id,
        target_message.message_id,
        target_message.from_user.id if target_message.from_user else None,
        vote_message.message_id,
    )
    bot.edit_message_reply_markup(
        chat_id=message.chat.id,
        message_id=vote_message.message_id,
        reply_markup=build_vote_keyboard(vote_id),
    )
    log_action(
        "vote_started",
        message.from_user.id if message.from_user else None,
        target_message.message_id,
        message.chat.id,
        f"Vote {vote_id} started",
    )
    return vote_id


def should_start_vote(message: Message, bot_username: str) -> bool:
    if not message.reply_to_message:
        return False
    text = message.text or message.caption or ""
    return f"@{bot_username}" in text


def handle_vote_callback(bot, call: CallbackQuery):
    if not call.data or not call.data.startswith(VOTE_PREFIX):
        return False
    payload = call.data[len(VOTE_PREFIX) :]
    vote_id_str, choice = payload.split(":", 1)
    vote_id = int(vote_id_str)
    vote = get_spam_vote(vote_id)
    if not vote:
        bot.answer_callback_query(call.id, "Голосование не найдено.")
        return True
    if vote["closed_at"]:
        bot.answer_callback_query(call.id, "Голосование уже закрыто.")
        return True
    if not is_verified_user(call.from_user.id):
        bot.answer_callback_query(call.id, "Только верифицированные участники могут голосовать.")
        return True
    created_at = vote["created_at"]
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if is_vote_expired(created_at):
        close_vote(bot, vote, reason="Голосование истекло.")
        bot.answer_callback_query(call.id, "Голосование истекло.")
        return True
    recorded = add_spam_vote(vote_id, call.from_user.id, "spam" if choice == "spam" else "ham")
    if not recorded:
        bot.answer_callback_query(call.id, "Ваш голос уже учтен.")
        return True
    counts = count_spam_votes(vote_id)
    if counts["spam"] >= SPAM_THRESHOLD:
        try:
            bot.delete_message(vote["chat_id"], vote["target_message_id"])
        except Exception:
            pass
        close_vote(bot, vote, reason="Порог спама достигнут.")
        log_action(
            "spam_deleted",
            vote.get("target_user_id"),
            vote["target_message_id"],
            vote["chat_id"],
            f"Vote {vote_id} reached threshold",
        )
    else:
        bot.answer_callback_query(call.id, "Голос учтен.")
    return True


def close_vote(bot, vote: dict, reason: str):
    close_spam_vote(vote["vote_id"])
    bot.edit_message_text(
        f"Голосование закрыто: {reason}",
        chat_id=vote["chat_id"],
        message_id=vote["poll_message_id"],
    )


def handle_vote_trigger(bot, message: Message, bot_username: str):
    close_expired_votes(bot)
    if should_start_vote(message, bot_username):
        create_vote(bot, message)


def close_expired_votes(bot):
    for vote in list_open_spam_votes():
        created_at = vote[\"created_at\"]
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if is_vote_expired(created_at):
            close_vote(bot, vote, reason=\"Голосование истекло.\")
