
import asyncio
import logging
import random
import string
from pathlib import Path

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ChatMemberHandler,
    ContextTypes,
    filters,
)

# ============== НАСТРОЙКИ ==============

TOKEN = "8905175157:AAHdpAr0MQnTiKdwsuCQsbsxd57IYm644UI"
OPENROUTER_API_KEY = "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"

ADMIN_ID = 8161017993
CHANNEL_ID = -1003939640142
CHANNEL_LINK = "https://t.me/+lyHMe0599OtjYjEy"

MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
PHOTO = Path(__file__).parent / "Start.jpg"

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# ============== КЛАВИАТУРЫ ==============

def kb(rows):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text, callback_data=data)]
        for text, data in rows
    ])


def sub_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_LINK)],
        [InlineKeyboardButton("🔄 Проверить подписку", callback_data="check_sub")],
    ])


def main_keyboard():
    return kb([
        ("🔤 Генератор юзов", "generator"),
        ("👤 Профиль", "profile"),
        ("🤖 AI Beta", "ai"),
        ("🔰 Вопрос к Ceko", "contact"),
    ])


def generator_keyboard():
    return kb([
        ("🎲 Случайный ник", "nick_random"),
        ("🔤 Ник на 5 букв", "nick5"),
        ("🔠 Ник на 7 букв", "nick7"),
        ("⬅️ Назад", "menu"),
    ])


def back_keyboard(target="menu"):
    return kb([("⬅️ Назад", target)])


# ============== ОТПРАВКА ЭКРАНОВ ==============

async def screen(chat_id, context, text, buttons=None):
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
            text="⚠️ Не найден файл Start.jpg\n\n" + text,
            reply_markup=buttons,
        )


async def subscribed(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ("member", "administrator", "creator")
    except TelegramError:
        logger.exception("Ошибка проверки подписки")
        return False


async def open_menu(chat_id, context):
    await screen(
        chat_id,
        context,
        "🌊 Ceko Hub Приветствует!\n\n"
        "Выбери нужный раздел.",
        main_keyboard(),
    )


# ============== СТАРТ ==============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data["contact_mode"] = False
    context.user_data["ai_mode"] = False

    if await subscribed(user.id, context):
        await open_menu(update.effective_chat.id, context)
    else:
        await screen(
            update.effective_chat.id,
            context,
            "🔰 Ceko Hub Приветствует!\n\n"
            "Чтобы продолжить, подпишись на канал.\n"
            "После подписки доступ откроется автоматически.",
            sub_keyboard(),
        )


# ============== АВТОДОСТУП ПОСЛЕ ПОДПИСКИ ==============

async def chat_member_update(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    change = update.chat_member
    if not change or change.chat.id != CHANNEL_ID:
        return

    old_status = change.old_chat_member.status
    new_status = change.new_chat_member.status

    was_subscribed = old_status in ("member", "administrator", "creator")
    is_subscribed = new_status in ("member", "administrator", "creator")

    if not was_subscribed and is_subscribed:
        user_id = change.new_chat_member.user.id

        try:
            await screen(
                user_id,
                context,
                "✅ Подписка подтверждена!\n\n"
                "Добро пожаловать в Ceko Hub!",
                main_keyboard(),
            )
        except TelegramError:
            logger.exception("Не удалось автоматически открыть меню")


# ============== ГЕНЕРАТОР ЮЗОВ ==============

def make_nick(length):
    return "".join(random.choices(string.ascii_lowercase, k=length))


async def generate_nick_screen(query, context, length):
    chat_id = query.message.chat_id

    await screen(chat_id, context, "🐍 Генерирую подходящий юз...")
    await asyncio.sleep(1.5)

    nickname = make_nick(length)

    await screen(
        chat_id,
        context,
        f"✨ Твой юз: {nickname}\n\n"
        f"Количество букв: {length}",
        kb([
            ( "🔄 Ещё вариант", f"nick{length}"),
            ("⬅️ К генератору", "generator"),
            ("🏠 Главное меню", "menu"),
        ]),
    )


# ============== ПРОФИЛЬ ==============

async def show_profile(query, context):
    user = query.from_user
    username = f"@{user.username}" if user.username else "Не установлен"

    await screen(
        query.message.chat_id,
        context,
        "👤 ПРОФИЛЬ\n\n"
        f"Имя: {user.first_name or 'Не указано'}\n"
        f"Username: {username}\n"
        f"ID: {user.id}",
        back_keyboard(),
    )


# ============== OPENROUTER AI ==============

def openrouter_request(messages):
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": "Ceko Hub AI Beta",
    }

    payload = {
        "model": MODEL,
        "messages": messages,
        "reasoning": {"enabled": True},
        "max_tokens": 1200,
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()

    choice = data["choices"][0]
    assistant_message = choice["message"]

    # Сохраняем полный объект ответа, включая reasoning_details,
    # чтобы передать их обратно при следующем запросе.
    return assistant_message


async def ai_reply(update, context, user_text):
    chat_id = update.effective_chat.id

    history = context.user_data.setdefault("ai_history", [])

    history.append({"role": "user", "content": user_text})

    # Ограничиваем историю, чтобы не раздувать запросы.
    history[:] = history[-16:]

    await screen(chat_id, context, "🤖 AI Beta думает...")

    try:
        answer = await asyncio.to_thread(
            openrouter_request,
            list(history),
        )

        content = answer.get("content")
        if not isinstance(content, str) or not content.strip():
            content = "Модель не вернула текстовый ответ. Попробуй ещё раз."

        history.append({
            "role": "assistant",
            "content": content,
            **(
                {"reasoning_details": answer["reasoning_details"]}
                if answer.get("reasoning_details") is not None
                else {}
            ),
        })
        history[:] = history[-16:]

        # Текстовые сообщения Telegram ограничены по длине.
        for start_index in range(0, len(content), 4000):
            await context.bot.send_message(
                chat_id=chat_id,
                text=content[start_index:start_index + 4000],
            )

        await screen(
            chat_id,
            context,
            "🤖 AI Beta\n\nНапиши следующий вопрос или выйди в меню.",
            kb([
                ("🧹 Очистить историю", "ai_clear"),
                ("⬅️ В меню", "menu"),
            ]),
        )

    except requests.RequestException:
        logger.exception("Ошибка запроса OpenRouter")
        await screen(
            chat_id,
            context,
            "⚠️ AI Beta временно недоступен.\n"
            "Проверь API-ключ, доступность модели и попробуй позже.",
            back_keyboard("ai"),
        )
    except (KeyError, IndexError, TypeError, ValueError):
        logger.exception("Неожиданный ответ OpenRouter")
        await screen(
            chat_id,
            context,
            "⚠️ Не удалось обработать ответ ИИ. Попробуй ещё раз.",
            back_keyboard("ai"),
        )


# ============== КНОПКИ ==============

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user = query.from_user
    chat_id = query.message.chat_id

    if data == "check_sub":
        if await subscribed(user.id, context):
            await open_menu(chat_id, context)
        else:
            await query.answer(
                "Подписка пока не обнаружена. Попробуй чуть позже.",
                show_alert=True,
            )
        return

    if not await subscribed(user.id, context):
        await screen(
            chat_id,
            context,
            "📢 Сначала подпишись на канал.",
            sub_keyboard(),
        )
        return

    if data == "menu":
        context.user_data["contact_mode"] = False
        context.user_data["ai_mode"] = False
        await open_menu(chat_id, context)

    elif data == "generator":
        context.user_data["contact_mode"] = False
        context.user_data["ai_mode"] = False
        await screen(
            chat_id,
            context,
            "🔤 ГЕНЕРАТОР ЮЗОВ\n\nВыбери вариант:",
            generator_keyboard(),
        )

    elif data == "profile":
        context.user_data["contact_mode"] = False
        context.user_data["ai_mode"] = False
        await show_profile(query, context)

    elif data in ("nick5", "nick7", "nick_random"):
        context.user_data["contact_mode"] = False
        context.user_data["ai_mode"] = False

        length = {
            "nick5": 5,
            "nick7": 7,
            "nick_random": random.randint(4, 10),
        }[data]

        await generate_nick_screen(query, context, length)

    elif data == "ai":
        context.user_data["contact_mode"] = False
        context.user_data["ai_mode"] = True
        await screen(
            chat_id,
            context,
            "🤖 AI BETA\n\n"
            "Напиши сообщение, и ИИ ответит.\n"
            "История диалога сохраняется до очистки или перезапуска бота.",
            kb([
                ("🧹 Очистить историю", "ai_clear"),
                ("⬅️ В меню", "menu"),
            ]),
        )

    elif data == "ai_clear":
        context.user_data["ai_history"] = []
        context.user_data["ai_mode"] = True
        await screen(
            chat_id,
            context,
            "🧹 История AI Beta очищена.\n\nНапиши новый вопрос.",
            back_keyboard("ai"),
        )

    elif data == "contact":
        context.user_data["ai_mode"] = False
        context.user_data["contact_mode"] = True
        await screen(
            chat_id,
            context,
            "🔰 ВОПРОС К CEKO\n\n"
            "Отправь сообщение, фото или файл. "
            "Я передам его администратору.",
            back_keyboard(),
        )


# ============== СООБЩЕНИЯ И СВЯЗЬ С АДМИНОМ ==============

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    # Ответ администратора на карточку обращения.
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
                await message.reply_text("✅ Ответ отправлен пользователю.")
            except (ValueError, StopIteration):
                await message.reply_text("❌ Не удалось определить пользователя.")
            except TelegramError:
                logger.exception("Ошибка отправки ответа")
                await message.reply_text("❌ Не удалось доставить ответ.")
        return

    if user.id == ADMIN_ID:
        return

    if not await subscribed(user.id, context):
        await screen(
            message.chat_id,
            context,
            "📢 Сначала подпишись на канал.",
            sub_keyboard(),
        )
        return

    # Сообщения в режиме AI Beta.
    if context.user_data.get("ai_mode"):
        if not message.text:
            await screen(
                message.chat_id,
                context,
                "Пока AI Beta принимает только текстовые сообщения.",
                back_keyboard("ai"),
            )
            return

        if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "ВСТАВЬ_OPENROUTER_API_KEY":
            await screen(
                message.chat_id,
                context,
                "⚠️ Сначала настрой API-ключ OpenRouter.",
                back_keyboard("ai"),
            )
            return

        await ai_reply(update, context, message.text)
        return

    # Сообщения администратору.
    if not context.user_data.get("contact_mode"):
        return

    username = f"@{user.username}" if user.username else "не установлен"
    info = (
        "📩 Сообщение от пользователя\n"
        f"Имя: {user.first_name or 'Не указано'}\n"
        f"Username: {username}\n"
        f"ID: {user.id}\n\n"
        "Ответь на это сообщение, чтобы написать пользователю."
    )

    try:
        await context.bot.send_message(ADMIN_ID, info)
        await context.bot.copy_message(
            chat_id=ADMIN_ID,
            from_chat_id=message.chat_id,
            message_id=message.message_id,
        )

        await screen(
            message.chat_id,
            context,
            "✅ Сообщение передано администратору.",
            back_keyboard(),
        )
    except TelegramError:
        logger.exception("Ошибка передачи сообщения")
        await screen(
            message.chat_id,
            context,
            "❌ Не удалось отправить сообщение. Попробуй позже.",
            back_keyboard(),
        )


# ============== ЗАПУСК ==============

def main():
    if not TOKEN or TOKEN == "ВСТАВЬ_НОВЫЙ_TELEGRAM_ТОКЕН":
        raise RuntimeError("Вставь новый токен Telegram-бота.")

    app = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(ChatMemberHandler(
        chat_member_update,
        ChatMemberHandler.CHAT_MEMBER,
    ))
    app.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, message_handler)
    )

    logger.info("Ceko Hub запущен")
    app.run_polling(
        allowed_updates=[
            "message",
            "callback_query",
            "chat_member",
        ]
    )


if __name__ == "__main__":
    main()
        
