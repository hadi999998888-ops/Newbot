
import asyncio
import logging
import random
import string
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ========== НАСТРОЙКИ ==========

TOKEN = "8905175157:AAHdpAr0MQnTiKdwsuCQsbsxd57IYm644UI"
ADMIN_ID = 8161017993
CHANNEL_ID = -1003939640142
CHANNEL_LINK = "https://t.me/+lyHMe0599OtjYjEy"
PHOTO = Path(__file__).parent / "Start.jpg"

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# ========== КНОПКИ ==========

def make_keyboard(rows):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text, callback_data=data) for text, data in row]
        for row in rows
    ])


def subscription_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Я подписался", callback_data="check_sub")],
    ])


def main_keyboard():
    return make_keyboard([
        [("Генератор юзов", "generator")],
        [("Профиль", "profile"), ("Связь с админом", "contact")],
    ])


def generator_keyboard():
    return make_keyboard([
        [("🎲 Случайный ник", "nick_random")],
        [("Ник на 5 букв", "nick5"), ("Ник на 7 букв", "nick7")],
        [("⬅️ Назад", "menu")],
    ])


def back_keyboard():
    return make_keyboard([[("⬅️ Назад", "menu")]])


# ========== ОТОБРАЖЕНИЕ START.JPG ==========

async def show_screen(chat_id, context, text, buttons=None):
    if PHOTO.is_file():
        with PHOTO.open("rb") as photo:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=text,
                reply_markup=buttons,
            )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ Файл Start.jpg не найден.\n\n{text}",
            reply_markup=buttons,
        )


# ========== ПРОВЕРКА ПОДПИСКИ ==========

async def is_subscribed(user_id, context):
    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id,
        )
        return member.status in ("member", "administrator", "creator")
    except TelegramError:
        logger.exception("Не удалось проверить подписку")
        return False


async def require_subscription(query, context):
    if await is_subscribed(query.from_user.id, context):
        return True

    await show_screen(
        query.message.chat_id,
        context,
        "📢 Чтобы продолжить, подпишись на канал и нажми кнопку проверки.",
        subscription_keyboard(),
    )
    return False


# ========== СТАРТ ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contact_mode"] = False

    await show_screen(
        update.effective_chat.id,
        context,
        f"Добро пожаловать в Ceko Hub, {update.effective_user.first_name}!\n\n"
        "Подпишись на канал, чтобы продолжить.",
        subscription_keyboard(),
    )


# ========== ГЕНЕРАТОР ЮЗОВ ==========

def generate_nick(length):
    letters = string.ascii_lowercase
    return "".join(random.choices(letters, k=length))


async def generate_nickname(query, context, length):
    chat_id = query.message.chat_id

    await show_screen(
        chat_id,
        context,
        "🐍 Рассматриваю варианты...",
    )

    await asyncio.sleep(2)

    nickname = generate_nick(length)

    await show_screen(
        chat_id,
        context,
        f"✨ Твой юз: {nickname}\n\n"
        f"Длина: {length} букв.",
        make_keyboard([
            [("🔄 Ещё вариант", f"nick{length}")],
            [("⬅️ К генератору", "generator")],
            [("🏠 Главное меню", "menu")],
        ]),
    )


# ========== ПРОФИЛЬ ==========

async def show_profile(query, context):
    user = query.from_user
    username = f"@{user.username}" if user.username else "Не установлен"

    await show_screen(
        query.message.chat_id,
        context,
        "👤 ПРОФИЛЬ\n\n"
        f"Имя: {user.first_name or 'Не указано'}\n"
        f"Username: {username}\n"
        f"ID: {user.id}",
        back_keyboard(),
    )


# ========== КНОПКИ ==========

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user = query.from_user
    chat_id = query.message.chat_id

    if data == "check_sub":
        if not await is_subscribed(user.id, context):
            await query.answer(
                "Подписка не найдена. Подпишись и попробуй снова.",
                show_alert=True,
            )
            return

        context.user_data["contact_mode"] = False
        await show_screen(
            chat_id,
            context,
            "✅ Подписка подтверждена!\n\nВыбери пункт меню.",
            main_keyboard(),
        )
        return

    if not await require_subscription(query, context):
        return

    if data == "menu":
        context.user_data["contact_mode"] = False
        await show_screen(
            chat_id,
            context,
            "Ceko Hub\n\nВыбери нужный раздел.",
            main_keyboard(),
        )

    elif data == "generator":
        context.user_data["contact_mode"] = False
        await show_screen(
            chat_id,
            context,
            "🔤 ГЕНЕРАТОР ЮЗОВ\n\nВыбери вариант генерации.",
            generator_keyboard(),
        )

    elif data == "profile":
        context.user_data["contact_mode"] = False
        await show_profile(query, context)

    elif data == "nick5":
        context.user_data["contact_mode"] = False
        await generate_nickname(query, context, 5)

    elif data == "nick7":
        context.user_data["contact_mode"] = False
        await generate_nickname(query, context, 7)

    elif data == "nick_random":
        context.user_data["contact_mode"] = False
        await generate_nickname(query, context, random.randint(4, 10))

    elif data == "contact":
        context.user_data["contact_mode"] = True
        await show_screen(
            chat_id,
            context,
            "💬 СВЯЗЬ С АДМИНОМ\n\n"
            "Отправь сообщение, фото или файл. "
            "Я передам его администратору.\n\n"
            "Чтобы выйти, нажми «Назад».",
            back_keyboard(),
        )


# ========== СООБЩЕНИЯ И ОТВЕТЫ АДМИНА ==========

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    # Ответ админа на карточку обращения пользователя
    if user.id == ADMIN_ID and message.reply_to_message:
        original = message.reply_to_message
        original_text = original.text or original.caption or ""

        if original_text.startswith("📩 Сообщение от пользователя"):
            try:
                id_line = next(
                    line for line in original_text.splitlines()
                    if line.startswith("ID:")
                )
                target_id = int(id_line.split(":", 1)[1].strip())

                await context.bot.copy_message(
                    chat_id=target_id,
                    from_chat_id=message.chat_id,
                    message_id=message.message_id,
                )
                await message.reply_text("✅ Ответ отправлен.")
            except (ValueError, StopIteration):
                await message.reply_text("❌ Не удалось определить пользователя.")
            except TelegramError:
                logger.exception("Ошибка доставки ответа")
                await message.reply_text("❌ Не удалось доставить ответ.")
        return

    if user.id == ADMIN_ID:
        return

    if not context.user_data.get("contact_mode"):
        return

    if not await is_subscribed(user.id, context):
        await show_screen(
            message.chat_id,
            context,
            "Сначала подпишись на канал.",
            subscription_keyboard(),
        )
        return

    username = f"@{user.username}" if user.username else "не установлен"

    info = (
        "📩 Сообщение от пользователя\n"
        f"Имя: {user.first_name or 'Не указано'}\n"
        f"Username: {username}\n"
        f"ID: {user.id}\n\n"
        "Ответь на это сообщение, чтобы ответить пользователю."
    )

    try:
        await context.bot.send_message(ADMIN_ID, info)
        await context.bot.copy_message(
            chat_id=ADMIN_ID,
            from_chat_id=message.chat_id,
            message_id=message.message_id,
        )

        await show_screen(
            message.chat_id,
            context,
            "✅ Сообщение отправлено администратору.",
            back_keyboard(),
        )
    except TelegramError:
        logger.exception("Ошибка пересылки")
        await show_screen(
            message.chat_id,
            context,
            "❌ Не удалось отправить сообщение. Попробуй позже.",
            back_keyboard(),
        )


# ========== ЗАПУСК ==========

def main():
    if TOKEN == "ВСТАВЬ_НОВЫЙ_ТОКЕН_ОТ_BOTFATHER":
        raise RuntimeError("Вставь новый токен бота в TOKEN.")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, message_handler)
    )

    logger.info("Ceko Hub запускается")
    app.run_polling()


if __name__ == "__main__":
    main()
     
