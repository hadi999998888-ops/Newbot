
import asyncio
import json
import os
import random
import string
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ChatType
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= НАСТРОЙКИ =================

TOKEN = os.getenv("BOT_TOKEN", "8905175157:AAEo3tBv5V1pJGbJwWRoRXojMyj5qaJAxfw")
ADMIN_ID = 8161017993
CHANNEL = "https://t.me/+lyHMe0599OtjYjEy"
PHOTO = "Start.jpg"

USERS_FILE = "users.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Временные данные
contact_mode = set()
admin_message_to_user = {}


# ================= ХРАНЕНИЕ =================

def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


users = load_users()


def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as file:
        json.dump(users, file, ensure_ascii=False, indent=2)


def register_user(user):
    uid = str(user.id)

    if uid not in users:
        users[uid] = {
            "id": user.id,
            "username": user.username or "",
            "first_name": user.first_name or "",
            "created": True,
        }
    else:
        users[uid]["username"] = user.username or ""
        users[uid]["first_name"] = user.first_name or ""

    save_users()


# ================= КЛАВИАТУРЫ =================

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Перейти в канал", url=CHANNEL)],
        [InlineKeyboardButton("🐍 Сгенерировать юз", callback_data="generator")],
        [InlineKeyboardButton("✉️ Обратиться", callback_data="contact")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
    ])


def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="menu")]
    ])


def generator_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("5 букв", callback_data="gen_5"),
            InlineKeyboardButton("7 букв", callback_data="gen_7"),
        ],
        [InlineKeyboardButton("🎲 Случайно", callback_data="gen_random")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="menu")],
    ])


# ================= ОТПРАВКА С ФОТО =================

async def send_screen(
    bot,
    chat_id,
    text,
    keyboard=None,
    reply_to_message_id=None,
):
    """Отправляет экран с Start.jpg и текстом в подписи."""

    try:
        with open(PHOTO, "rb") as photo:
            return await bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=text,
                reply_markup=keyboard,
                reply_to_message_id=reply_to_message_id,
            )
    except FileNotFoundError:
        logging.error("Не найден файл %s", PHOTO)
        return await bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ Не найден файл {PHOTO}\n\n{text}",
            reply_markup=keyboard,
            reply_to_message_id=reply_to_message_id,
        )


async def update_screen(query, text, keyboard=None):
    """Обновляет текст текущего экрана."""

    try:
        await query.edit_message_caption(
            caption=text,
            reply_markup=keyboard,
        )
    except TelegramError:
        await send_screen(
            query.get_bot(),
            query.message.chat_id,
            text,
            keyboard,
        )


# ================= СТАРТ =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)
    contact_mode.discard(user.id)

    text = (
        "🪷 Добро пожаловать в Ceko Hub!\n\n"
        "🔸 Много разных функций.\n"
        "Пользуйся и обращайся к владельцу!\n\n"
        "Выбери пункт:"
    )

    await send_screen(
        context.bot,
        update.effective_chat.id,
        text,
        main_keyboard(),
    )


# ================= ГЕНЕРАТОР =================

def generate_username(length):
    alphabet = string.ascii_lowercase
    return "".join(random.choice(alphabet) for _ in range(length))


async def generator_start(query):
    await update_screen(
        query,
        "🔸 Выбери пункт 🔸\n\n"
        "🐍 Генератор юзернеймов",
        generator_keyboard(),
    )


async def generate_username_flow(query, context, length):
    await update_screen(
        query,
        "🐍 Рассматриваю...",
        None,
    )

    await asyncio.sleep(2)

    await update_screen(
        query,
        "🐍 Отправляю...",
        None,
    )

    await asyncio.sleep(2)

    username = generate_username(length)

    await update_screen(
        query,
        f"✅ Готово!\n\n"
        f"👤 Юзернейм: @{username}\n"
        f"🔢 Длина: {length} букв\n\n"
        "⚠️ Это случайная комбинация. "
        "Её доступность в Telegram не проверяется.",
        InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Ещё раз", callback_data="generator")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="menu")],
        ]),
    )


# ================= ПРОФИЛЬ =================

async def show_profile(query):
    user = query.from_user
    register_user(user)

    username = f"@{user.username}" if user.username else "Не установлен"
    first_name = user.first_name or "Не указано"

    text = (
        "👤 ТВОЙ ПРОФИЛЬ\n\n"
        f"🔹 Имя: {first_name}\n"
        f"🔹 Юзернейм: {username}\n"
        f"🆔 ID: {user.id}\n\n"
        "Добро пожаловать в Ceko Hub!"
    )

    await update_screen(query, text, back_keyboard())


# ================= ОБРАЩЕНИЕ К АДМИНУ =================

async def contact_start(query, context):
    user = query.from_user
    contact_mode.add(user.id)

    await update_screen(
        query,
        "🔸 Напиши любое сообщение.\n\n"
        "Принимаю текст, фото, видео, документы "
        "и другие поддерживаемые форматы.\n\n"
        "📨 Сообщение будет передано владельцу Ceko Hub.\n"
        "Для отмены напиши /cancel",
        back_keyboard(),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    contact_mode.discard(user.id)

    await send_screen(
        context.bot,
        update.effective_chat.id,
        "❌ Обращение отменено.\n\nВыбери пункт меню:",
        main_keyboard(),
    )


async def receive_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message

    if not message or user.id not in contact_mode:
        return

    if user.id == ADMIN_ID:
        return

    admin_info = (
        "📩 НОВОЕ ОБРАЩЕНИЕ — CEKO HUB\n\n"
        f"👤 Имя: {user.first_name or 'Не указано'}\n"
        f"🔹 Юзернейм: "
        f"@{user.username if user.username else 'не установлен'}\n"
        f"🆔 ID пользователя: {user.id}\n\n"
        "↩️ Ответь через Reply на это сообщение "
        "или на пересланное ниже сообщение."
    )

    try:
        info_message = await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_info,
        )

        copied_message = await context.bot.copy_message(
            chat_id=ADMIN_ID,
            from_chat_id=message.chat_id,
            message_id=message.message_id,
        )

        admin_message_to_user[info_message.message_id] = user.id
        admin_message_to_user[copied_message.message_id] = user.id

        contact_mode.discard(user.id)

        await send_screen(
            context.bot,
            user.id,
            "✅ Твоё сообщение отправлено владельцу Ceko Hub!\n\n"
            "Ожидай ответа.",
            main_keyboard(),
        )

    except TelegramError as error:
        logging.exception("Не удалось передать обращение: %s", error)

        await send_screen(
            context.bot,
            user.id,
            "❌ Не удалось отправить сообщение.\n"
            "Попробуй ещё раз немного позже.",
            back_keyboard(),
        )


# ================= ОТВЕТ АДМИНА =================

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if not message or not message.reply_to_message:
        return

    if update.effective_user.id != ADMIN_ID:
        return

    replied_id = message.reply_to_message.message_id
    target_user_id = admin_message_to_user.get(replied_id)

    if not target_user_id:
        return

    try:
        # Копируем ответ администратора в исходном формате:
        # текст, фото, видео, документ и другие поддерживаемые типы.
        await context.bot.copy_message(
            chat_id=target_user_id,
            from_chat_id=message.chat_id,
            message_id=message.message_id,
        )

        await send_screen(
            context.bot,
            target_user_id,
            "📩 Ответ от владельца Ceko Hub",
            main_keyboard(),
        )

        await send_screen(
            context.bot,
            ADMIN_ID,
            "✅ Ответ доставлен пользователю.",
            back_keyboard(),
        )

    except TelegramError as error:
        logging.exception("Не удалось доставить ответ: %s", error)

        await send_screen(
            context.bot,
            ADMIN_ID,
            "❌ Не удалось доставить ответ пользователю.",
            back_keyboard(),
        )


# ================= ОБРАБОТКА КНОПОК =================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    register_user(user)

    data = query.data

    if data == "menu":
        contact_mode.discard(user.id)

        await update_screen(
            query,
            "🪷 Ceko Hub\n\nВыбери пункт:",
            main_keyboard(),
        )

    elif data == "generator":
        await generator_start(query)

    elif data == "gen_5":
        await generate_username_flow(query, context, 5)

    elif data == "gen_7":
        await generate_username_flow(query, context, 7)

    elif data == "gen_random":
        length = random.randint(5, 10)
        await generate_username_flow(query, context, length)

    elif data == "profile":
        await show_profile(query)

    elif data == "contact":
        await contact_start(query, context)


# ================= ЗАПУСК =================

def main():
    if not TOKEN or TOKEN == "ВСТАВЬ_СЮДА_ТОКЕН_БОТА":
        raise SystemExit(
            "Ошибка: вставь токен бота в переменную TOKEN в начале файла."
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))

    # Ответы админа через Reply обрабатываются раньше обычных сообщений.
    app.add_handler(
        MessageHandler(
            filters.Chat(chat_id=ADMIN_ID) & filters.REPLY,
            admin_reply,
        )
    )

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            receive_contact,
        )
    )

    print("Ceko Hub запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
