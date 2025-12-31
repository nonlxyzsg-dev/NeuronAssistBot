from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery, ChatPermissions
from db import is_user_verified, add_verified_user, log_action


def handle_new_member(bot: TeleBot, message: Message):
    for user in message.new_chat_members:
        if is_user_verified(user.id):
            continue
        restrict_permissions = ChatPermissions(can_send_messages=False, can_send_other_messages=False)
        bot.restrict_chat_member(message.chat.id, user.id, permissions=restrict_permissions)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Я не бот", callback_data=f"verify:{user.id}"))
        bot.send_message(
            message.chat.id,
            f"{user.first_name}, подтвердите, что вы не бот",
            reply_markup=markup,
        )
        log_action(user.id, "restricted_new_member", None, "awaiting_verification")


def handle_verification(bot: TeleBot, call: CallbackQuery):
    data = call.data
    if not data or not data.startswith("verify:"):
        return
    target_user_id = int(data.split(":", 1)[1])
    if call.from_user.id != target_user_id:
        bot.answer_callback_query(call.id, "Эта кнопка не для вас")
        return
    allow_permissions = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_change_info=False,
        can_invite_users=True,
        can_pin_messages=False,
    )
    bot.restrict_chat_member(call.message.chat.id, target_user_id, permissions=allow_permissions)
    add_verified_user(target_user_id)
    log_action(target_user_id, "user_verified", call.message.message_id, "verification_complete")
    bot.edit_message_text(
        "Верификация пройдена! Добро пожаловать.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )
    bot.answer_callback_query(call.id, "Спасибо за подтверждение!")
