
import logging
import random
import string
import asyncio
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
CHANNEL_LINK = "https://t.me/+lyHMe0599OtjYjEy"

# Укажи ID канала для реальной проверки подписки.
# Пока не настроено, оставь None.
CHANNEL_ID = None

PHOTO = Path(__file__).parent / "Start.jpg"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# ========== ОБЩИЕ ФУНКЦИИ ==========

def keyboard(rows):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text, callback_data=data)
         for text, data in row]
        for row in rows
    ])


def subscription_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Подписаться", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Я подписался", callback_data="check_subscription")],
    ])


def main_keyboard():
    return keyboard([
        [("🛒 Купить фулл", "buy_full"),
         ("📦 Выставить товар", "sell_item")],
        [("👤 Профиль", "profile")],
        [("🔤 Ник на 5 букв", "nick5"),
         ("🔠 Ник на 7 букв", "nick7")],
        [("🎰 Случайный ник", "nick_random")],
        [("💬 Связаться с админом", "contact")],
    ])


def back_keyboard():
    return keyboard([
        [("⬅️ В меню", "menu")]
    ])


async def show_screen(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup=None,
):
    """Показывает Start.jpg во всех разделах."""
    chat_id = update.effective_chat.id

    if PHOTO.exists():
        with PHOTO.open("rb") as photo:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=text,
                reply_markup=reply_markup,
            )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ Не найден файл Start.jpg\n\n{text}",
            reply_markup=reply_markup,
        )


async def edit_or_show_screen(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup=None,
):
    """
    Отправляет новое сообщение с Start.jpg.
    Предыдущее сообщение не удаляется.
    """
    chat_id = query.message.chat_id

    if PHOTO.exists():
        with PHOTO.open("rb") as photo:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=text,
                reply_markup=reply_markup,
            )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ Не найден файл Start.jpg\n\n{text}",
            reply_markup=reply_markup,
        )


async def is_subscribed(user_id, context):
    if CHANNEL_ID is None:
        return False

    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id,
        )
        return member.status in ("member", "administrator", "creator")
    except TelegramError:
        logger.exception("Ошибка проверки подписки")
        return False


# ========== START ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contact_mode"] = False

    await show_screen(
        update,
        context,
        f"👋 Привет, {update.effective_user.first_name}!\n\n"
        "Добро пожаловать в Ceko Hub.\n\n"
        "📢 Подпишись на канал, чтобы продолжить.",
        subscription_keyboard(),
    )


# ========== ПРОФИЛЬ ==========

async def profile_screen(query, context):
    user = query.from_user
    username = f"@{user.username}" if user.username else "Не установлен"

    await edit_or_show_screen(
        query,
        context,
        "👤 ТВОЙ ПРОФИЛЬ\n\n"
        f"Имя: {user.first_name or 'Не указано'}\n"
        f"Username: {username}\n"
        f"ID: {user.id}\n\n"
        "Добро пожаловать в Ceko Hub!",
        back_keyboard(),
    )


# ========== ГЕНЕРАТОР НИКОВ ==========

def generate_nickname(length):
    return "".join(
        random.choice(string.ascii_lowercase)
        for _ in range(length)
    )


async def nickname_screen(query, context, length):
    await edit_or_show_screen(
        query,
        context,
        "🐍 Рассматриваю варианты...",
    )

    await asyncio.sleep(2)

    nickname = generate_nickname(length)

    await edit_or_show_screen(
        query,
        context,
        "🐍 Отправляю результат...",
    )

    await asyncio.sleep(2)

    await edit_or_show_screen(
        query,
        context,
        f"✨ Твой ник: {nickname}\n\n"
        "Ник сгенерирован случайно.",
        keyboard([
            [( "🔄 Ещё вариант", f"nick{length}")],
            [("⬅️ В меню", "menu")],
        ]),
    )


# ========== ОБРАБОТКА КНОПОК ==========

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user = query.from_user

    if data == "check_subscription":
        if CHANNEL_ID is None:
            await edit_or_show_screen(
                query,
                context,
                "⚙️ Проверка подписки ещё не настроена.\n\n"
                "Администратору нужно указать ID канала "
                "в настройках bot.py.",
                back_keyboard(),
            )
            return

        if not await is_subscribed(user.id, context):
            await query.answer(
                "❌ Подписка не найдена. Подпишись и попробуй снова.",
                show_alert=True,
            )
            return

        context.user_data["contact_mode"] = False
        await edit_or_show_screen(
            query,
            context,
            "✅ Подписка подтверждена!\n\n"
            "Выбери пункт из меню.\n"
            "Все без скама ❗",
            main_keyboard(),
        )
        return

    # Когда ID канала задан, проверяем подписку перед доступом к меню.
    if CHANNEL_ID is not None:
        if not await is_subscribed(user.id, context):
            await edit_or_show_screen(
                query,
                context,
                "📢 Сначала подпишись на канал, чтобы продолжить.",
                subscription_keyboard(),
            )
            return

    if data == "menu":
        context.user_data["contact_mode"] = False
        await edit_or_show_screen(
            query,
            context,
            "🏠 Ceko Hub\n\nВыбери пункт из меню.\n"
            "Все без скама ❗",
            main_keyboard(),
        )

    elif data == "profile":
        await profile_screen(query, context)

    elif data == "nick5":
        await nickname_screen(query, context, 5)

    elif data == "nick7":
        await nickname_screen(query, context, 7)

    elif data == "nick_random":
        await nickname_screen(query, context, random.randint(4, 10))

    elif data == "buy_full":
        await edit_or_show_screen(
            query,
            context,
            "🛒 КУПИТЬ ФУЛЛ\n\n"
            "🔸 Выбери нужный товар.\n\n"
            "Каталог товаров пока не добавлен. "
            "Для заказа свяжись с администратором.",
            keyboard([
                [("💬 Связаться с админом", "contact")],
                [("⬅️ В меню", "menu")],
            ]),
        )

    elif data == "sell_item":
        await edit_or_show_screen(
            query,
            context,
            "📦 ВЫСТАВИТЬ ТОВАР\n\n"
            "Чтобы обсудить размещение товара, "
            "нажми кнопку связи с администратором.",
            keyboard([
                [("💬 Связаться с админом", "contact")],
                [("⬅️ В меню", "menu")],
            ]),
        )

    elif data == "contact":
        context.user_data["contact_mode"] = True
        await edit_or_show_screen(
            query,
            context,
            "💬 СВЯЗЬ С АДМИНИСТРАТОРОМ\n\n"
            "Отправь сообщение, фото или файл — "
            "я передам его администратору.\n\n"
            "Чтобы выйти из режима связи, нажми «В меню».",
            back_keyboard(),
        )


# ========== СООБЩЕНИЯ И ОТВЕТЫ АДМИНА ==========

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    # Администратор отвечает на сообщение с ID клиента.
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
                await message.reply_text(
                    "❌ Не удалось найти ID пользователя."
                )
            except TelegramError:
                logger.exception("Ошибка отправки ответа")
                await message.reply_text(
                    "❌ Не удалось доставить ответ пользователю."
                )
            return

    if user.id == ADMIN_ID:
        return

    if not context.user_data.get("contact_mode", False):
        await show_screen(
            update,
            context,
            "Чтобы написать администратору, выбери этот пункт в меню.",
            keyboard([
                [("💬 Связаться с админом", "contact")],
                [("⬅️ В меню", "menu")],
            ]),
        )
        return

    username = f"@{user.username}" if user.username else "нет username"

    info = (
        "📩 Сообщение от пользователя\n"
        f"Имя: {user.first_name or 'Не указано'}\n"
        f"Username: {username}\n"
        f"ID: {user.id}\n\n"
        "Ответь на это служебное сообщение, чтобы отправить ответ."
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=info,
        )

        await context.bot.copy_message(
            chat_id=ADMIN_ID,
            from_chat_id=message.chat_id,
            message_id=message.message_id,
        )

        await show_screen(
            update,
            context,
            "✅ Сообщение передано администратору.",
            back_keyboard(),
        )

    except TelegramError:
        logger.exception("Не удалось переслать сообщение админу")
        await show_screen(
            update,
            context,
            "❌ Не получилось отправить сообщение. Попробуй позже.",
            back_keyboard(),
        )


# ========== ЗАПУСК ==========

def main():
    if TOKEN == "ВСТАВЬ_НОВЫЙ_ТОКЕН_ОТ_BOTFATHER":
        raise RuntimeError("Сначала вставь новый токен в TOKEN.")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, message_handler)
    )

    logger.info("Ceko Hub запускается...")
    app.run_polling()


if __name__ == "__main__":
    main()
        
