from telebot import types
from telebot.types import CallbackQuery, Message

from db import add_verified_user, is_verified_user, log_action


VERIFY_PREFIX = "verify:"


def restrict_user(bot, chat_id: int, user_id: int):
    permissions = types.ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_polls=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False,
        can_change_info=False,
        can_invite_users=False,
        can_pin_messages=False,
    )
    bot.restrict_chat_member(chat_id, user_id, permissions=permissions)


def unrestrict_user(bot, chat_id: int, user_id: int):
    permissions = types.ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_change_info=False,
        can_invite_users=True,
        can_pin_messages=False,
    )
    bot.restrict_chat_member(chat_id, user_id, permissions=permissions)


def handle_new_chat_members(bot, message: Message):
    for user in message.new_chat_members:
        if is_verified_user(user.id):
            continue
        restrict_user(bot, message.chat.id, user.id)
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                text="✅ Я не бот",
                callback_data=f"{VERIFY_PREFIX}{user.id}",
            )
        )
        bot.send_message(
            message.chat.id,
            f"Привет, {user.first_name}! Подтверди, что ты не бот.",
            reply_markup=keyboard,
        )
        log_action(
            "verification_required",
            user.id,
            message.message_id,
            message.chat.id,
            "User restricted pending verification",
        )


def handle_verify_callback(bot, call: CallbackQuery):
    if not call.data or not call.data.startswith(VERIFY_PREFIX):
        return False
    user_id = int(call.data.split(":", 1)[1])
    if call.from_user.id != user_id:
        bot.answer_callback_query(call.id, "Эта кнопка не для вас.")
        return True
    unrestrict_user(bot, call.message.chat.id, user_id)
    add_verified_user(user_id)
    log_action(
        "verified",
        user_id,
        call.message.message_id,
        call.message.chat.id,
        "User verified via button",
    )
    bot.edit_message_text(
        "✅ Верификация пройдена!",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )
    bot.answer_callback_query(call.id, "Спасибо, доступ открыт!")
    return True
