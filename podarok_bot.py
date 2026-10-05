#!/usr/bin/env python3
"""
Бот @svami_podarok_bot — урок «Как считывать намерения другого человека»
"""

import asyncio
import json
import os
import logging
import aiohttp
from datetime import datetime, timedelta
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
    ContextTypes,
)

# ─── НАСТРОЙКИ ────────────────────────────────────────────────────────────────
TOKEN             = os.environ["PODAROK_BOT_TOKEN"]
ADMIN_CHAT_ID     = os.getenv("ADMIN_CHAT_ID", "")
SHEET_URL         = os.getenv("SHEET_URL", "")
YOOKASSA_TOKEN    = os.getenv("YOOKASSA_TOKEN", "")
COURSE_CHANNEL_ID = os.getenv("COURSE_CHANNEL_ID", "")

BASE = os.path.dirname(__file__)
LESSON_COVER_PATH   = os.path.join(BASE, "images", "lesson_cover.jpg")
PDF_PATH            = os.path.join(BASE, "Эмоции и потребности.pdf")
KRUZHOK_1_PATH      = os.path.join(BASE, "kruzhok_1.mp4")
KRUZHOK_2_PATH      = os.path.join(BASE, "kruzhok_2.mp4")
KRUZHOK_DIAG_PATH   = os.path.join(BASE, "kruzhok_diagnostic.mp4")

LESSON_URL = "https://youtu.be/iDxW8sOII98"

paid_users: set = set()

logging.basicConfig(
    format="%(asctime)s · %(name)s · %(levelname)s · %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── ВАРИАНТЫ ОТВЕТОВ ─────────────────────────────────────────────────────────
CHOICES = {
    "c1": "Разрешать конфликты в отношениях с партнёром, друзьями, родственниками",
    "c2": "Повысить эффективность переговоров в рабочей команде",
    "c3": "Получать положительный результат при заключении сделок",
    "c4": "Прокачать сверхспособности",
    "c5": "Лучше понимать людей",
    "c6": "Экологично получать от людей то, что мне нужно",
}

CHOICE_INTROS = {
    "c1": "Если ты хочешь разрешать конфликты в отношениях с партнёром, друзьями и родственниками",
    "c2": "Если ты хочешь повысить эффективность переговоров в рабочей команде",
    "c3": "Если ты хочешь получать положительный результат при заключении сделок",
    "c4": "Если ты хочешь прокачать сверхспособности",
    "c5": "Если ты хочешь лучше понимать людей",
    "c6": "Если ты хочешь экологично получать от людей то, что тебе нужно",
}

# ─── GOOGLE SHEETS ────────────────────────────────────────────────────────────
async def log_to_sheet(event: str, **kwargs):
    if not SHEET_URL:
        return
    try:
        params = {"event": event, **{k: str(v) for k, v in kwargs.items()}}
        async with aiohttp.ClientSession() as session:
            await session.post(
                SHEET_URL, data=params,
                timeout=aiohttp.ClientTimeout(total=6),
                allow_redirects=True,
            )
    except Exception as exc:
        logger.warning("Sheet log skipped: %s", exc)


# ══════════════════════════════════════════════════════════════════════════════
# /start — выбор цели
# ══════════════════════════════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    asyncio.create_task(log_to_sheet(
        "start",
        name=f"{user.first_name or ''} {user.last_name or ''}".strip(),
        username=f"@{user.username}" if user.username else "",
        user_id=user.id,
        bot="podarok",
    ))
    await update.message.reply_text(
        "Выберите, зачем вам считывать намерение человека:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(CHOICES["c1"], callback_data="c1")],
            [InlineKeyboardButton(CHOICES["c2"], callback_data="c2")],
            [InlineKeyboardButton(CHOICES["c3"], callback_data="c3")],
            [InlineKeyboardButton(CHOICES["c4"], callback_data="c4")],
            [InlineKeyboardButton(CHOICES["c5"], callback_data="c5")],
            [InlineKeyboardButton(CHOICES["c6"], callback_data="c6")],
        ]),
    )


# ══════════════════════════════════════════════════════════════════════════════
# ВЫБОР ВАРИАНТА → урок
# ══════════════════════════════════════════════════════════════════════════════
async def choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    choice_key = q.data
    intro = CHOICE_INTROS.get(choice_key, "")
    chat_id = q.message.chat_id
    bot_ref = context.bot

    # Отправляем обложку + текст урока
    lesson_text = (
        f"{intro} — рекомендую посмотреть этот урок.\n\n"
        "🎬 *«Как считывать намерения другого человека»*\n\n"
        "В нём я рассказываю, как понять, что человек думает на самом деле, даже если молчит. "
        "Почему вы не слышите сигналы интуиции во время разговора. "
        "Даю конкретный алгоритм считывания намерения человека.\n\n"
        f"👇 Смотреть урок:\n{LESSON_URL}\n\n"
        "0:00 — Почему мы ошибаемся в людях\n"
        "0:35 — Слова и намерение — в чём разница\n"
        "1:30 — 3 уровня считывания человека\n"
        "3:10 — Шаг 1: выйти в позицию наблюдателя\n"
        "4:20 — Шаг 2: правильные внутренние вопросы\n"
        "5:30 — Шаг 3: перестать читать буквально\n"
        "7:00 — Что делать с полученной информацией\n"
        "8:30 — Почему это не работает в стрессе\n"
        "9:15 — Как развить этот навык системно"
    )
    try:
        with open(LESSON_COVER_PATH, "rb") as cover:
            await bot_ref.send_photo(chat_id=chat_id, photo=cover)
    except Exception as exc:
        logger.warning("Lesson cover failed: %s", exc)

    await bot_ref.send_message(
        chat_id=chat_id,
        text=lesson_text,
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )

    # Запускаем цепочку отложенных сообщений
    asyncio.create_task(send_follow_up_chain(bot_ref, chat_id))


# ══════════════════════════════════════════════════════════════════════════════
# ЦЕПОЧКА: PDF → кружки → курс
# ══════════════════════════════════════════════════════════════════════════════
async def send_follow_up_chain(bot, chat_id: int):
    # 1 — через 3 мин: PDF «Эмоции и потребности»
    await asyncio.sleep(3 * 60)
    try:
        with open(PDF_PATH, "rb") as pdf:
            await bot.send_document(
                chat_id=chat_id,
                document=pdf,
                filename="Эмоции и потребности.pdf",
            )
    except Exception as exc:
        logger.warning("PDF send failed: %s", exc)

    # 2 — через 15 мин: два кружка + описание курса
    await asyncio.sleep(15 * 60)

    for path, label in [(KRUZHOK_1_PATH, "Kruzhok 1"), (KRUZHOK_2_PATH, "Kruzhok 2")]:
        try:
            with open(path, "rb") as f:
                await asyncio.wait_for(
                    bot.send_video_note(chat_id=chat_id, video_note=f),
                    timeout=60,
                )
        except Exception as exc:
            logger.warning("%s failed: %s", label, exc)

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "✨ *Курс «Основы управления интуицией»*\n\n"
                "За 1 неделю ты освоишь, а за 1 месяц прокачаешь "
                "базовый навык считывания любой информации\n\n"
                "*До курса:*\n"
                "· Чувствуете, что человеку нельзя доверять, но не можете объяснить почему\n"
                "· Соглашаетесь вопреки внутреннему ощущению, а потом жалеете\n"
                "· Испытываете напряжение, когда нужно быстрое решение в условиях неопределённости\n"
                "· Игнорируете интуицию или принимаете импульсивные решения\n\n"
                "*После курса:*\n"
                "· Считываете людей — эмоции, намерения, скрытые мотивы\n"
                "· Принимаете точные решения когда данных и времени мало\n"
                "· Прогнозируете исходы переговоров, партнёрств, сделок\n"
                "· Видите ситуацию на шаг вперёд\n"
                "· Понимаете, как избежать конфликт с близкими\n\n"
                "*Что включено:*\n"
                "— 7 уроков до 20 минут\n"
                "— Практические задания на каждый день\n"
                "— Обратная связь от Марии в телеграме\n"
                "— Сообщество развивающихся людей\n"
                "— Доступ на 1 месяц"
            ),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Активировать спец. условия", callback_data="spec_offer"),
            ]]),
        )
    except Exception as exc:
        logger.warning("Course message failed: %s", exc)


# ══════════════════════════════════════════════════════════════════════════════
# СПЕЦУСЛОВИЯ
# ══════════════════════════════════════════════════════════════════════════════
async def spec_offer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_text(
        "🔥 *Специальные условия для тебя*\n"
        "Стандартная цена курса: ~6 990 ₽~\n"
        "→ *2 990 ₽* \\(скидка *4 000 ₽*\\)\n\n"
        "Только 60 минут цена для тебя снижена\n"
        "После — стоимость вернётся к стандартной 🕐",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Приобрести курс за 2990 ₽", callback_data="buy_course"),
        ]]),
    )
    asyncio.create_task(delayed_no_payment_reminder(
        context.bot, q.message.chat_id, q.from_user.id
    ))


# ══════════════════════════════════════════════════════════════════════════════
# КНОПКА «Приобрести» → согласие
# ══════════════════════════════════════════════════════════════════════════════
async def buy_course_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user
    asyncio.create_task(log_to_sheet(
        "payment_bot_buy_click",
        user_id=user.id,
        name=f"{user.first_name or ''} {user.last_name or ''}".strip(),
        username=f"@{user.username}" if user.username else "",
        bot="podarok",
    ))
    await q.message.reply_text(
        'Нажимая кнопку "Оплатить", вы соглашаетесь:\n\n'
        '☑️ Я ознакомлен(а) с <a href="https://maria-alpidovskaya.ru/oferta">публичной Офертой</a>\n\n'
        '☑️ Я ознакомлен(а) с <a href="https://maria-alpidovskaya.ru/politika-opd">Политикой обработки персональных данных</a> '
        'и с <a href="https://maria-alpidovskaya.ru/soglasie-opd">Согласием на обработку персональных данных</a>\n\n'
        '☑️ Я даю согласие на получение бесплатных гайдов, памяток, чек-листов, а также иных материалов '
        'информационного и рекламного характера, в том числе посредством sms-уведомления.',
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("💳 Оплатить", callback_data="pay_now"),
        ]]),
    )


# ══════════════════════════════════════════════════════════════════════════════
# КНОПКА «Оплатить» → invoice
# ══════════════════════════════════════════════════════════════════════════════
async def pay_now_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user
    asyncio.create_task(log_to_sheet(
        "payment_bot_invoice_sent",
        user_id=user.id,
        name=f"{user.first_name or ''} {user.last_name or ''}".strip(),
        username=f"@{user.username}" if user.username else "",
        bot="podarok",
    ))
    receipt_data = json.dumps({
        "receipt": {
            "items": [{
                "description": "Курс «Основы управления интуицией»",
                "quantity": 1,
                "amount": {"value": "2990.00", "currency": "RUB"},
                "vat_code": 1,
                "payment_mode": "full_payment",
                "payment_subject": "service",
            }],
            "tax_system_code": 2,
        }
    }, ensure_ascii=False)
    try:
        await context.bot.send_invoice(
            chat_id=q.message.chat_id,
            title="Курс «Основы управления интуицией»",
            description="Доступ к курсу на 1 месяц",
            payload="course_intuition_2990",
            provider_token=YOOKASSA_TOKEN,
            currency="RUB",
            prices=[LabeledPrice("Курс «Основы управления интуицией»", 299000)],
            provider_data=receipt_data,
            need_name=True,
            need_email=True,
            send_email_to_provider=True,
            need_phone_number=True,
        )
    except Exception as e:
        logger.error("send_invoice failed: %s", e)
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text="Не удалось открыть оплату. Попробуйте ещё раз или напишите нам.",
        )


# ══════════════════════════════════════════════════════════════════════════════
# PRE-CHECKOUT + УСПЕШНАЯ ОПЛАТА
# ══════════════════════════════════════════════════════════════════════════════
async def pre_checkout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    paid_users.add(user.id)

    purchase_date = datetime.now().strftime("%d.%m.%Y")
    expiry_date   = (datetime.now() + timedelta(days=30)).strftime("%d.%m.%Y")

    channel_link = "https://t.me/+VNnNxLOM3BE5NTEy"
    if COURSE_CHANNEL_ID:
        try:
            invite = await context.bot.create_chat_invite_link(
                chat_id=int(COURSE_CHANNEL_ID), member_limit=1,
            )
            channel_link = invite.invite_link
        except Exception as exc:
            logger.warning("Channel invite failed: %s", exc)

    await update.message.reply_text(
        f"✅ Оплата прошла успешно!\n\n"
        f"Вот твоя персональная ссылка для входа в курс:\n{channel_link}\n\n"
        f"Доступ действует до {expiry_date}. Добро пожаловать! 🎉"
    )

    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "—"
    tg   = f"@{user.username}" if user.username else ""
    asyncio.create_task(log_to_sheet(
        "purchase",
        user_id=user.id,
        name=name,
        username=tg,
        purchase_date=purchase_date,
        expiry_date=expiry_date,
        amount="2990",
        bot="podarok",
    ))

    if ADMIN_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=(
                    "💰 *Новая оплата курса (podarok bot)*\n\n"
                    f"👤 {name}\n"
                    f"📱 {tg}  |  ID: `{user.id}`\n"
                    f"💵 Сумма: 2 990 ₽\n"
                    f"📅 Доступ до: {expiry_date}"
                ),
                parse_mode="Markdown",
            )
        except Exception as exc:
            logger.warning("Admin notify failed: %s", exc)

    asyncio.create_task(delayed_renewal_reminder(context.bot, update.message.chat_id, user.id))


# ══════════════════════════════════════════════════════════════════════════════
# НАПОМИНАНИЕ ЧЕРЕЗ 60 МИН (не оплатил)
# ══════════════════════════════════════════════════════════════════════════════
async def delayed_no_payment_reminder(bot, chat_id: int, user_id: int):
    await asyncio.sleep(60 * 60)
    if user_id in paid_users:
        return

    try:
        with open(KRUZHOK_DIAG_PATH, "rb") as f:
            await asyncio.wait_for(
                bot.send_video_note(chat_id=chat_id, video_note=f),
                timeout=60,
            )
    except Exception as exc:
        logger.warning("Diagnostic kruzhok failed: %s", exc)

    try:
        diag_url = "https://t.me/svami_assistent?text=%D0%97%D0%B4%D1%80%D0%B0%D0%B2%D1%81%D1%82%D0%B2%D1%83%D0%B9%D1%82%D0%B5%2C%20%D1%85%D0%BE%D1%87%D1%83%20%D0%B7%D0%B0%D0%BF%D0%B8%D1%81%D0%B0%D1%82%D1%8C%D1%81%D1%8F%20%D0%BA%20%D0%9C%D0%B0%D1%80%D0%B8%D0%B8%20%D0%BD%D0%B0%20%D0%BB%D0%B8%D1%87%D0%BD%D1%83%D1%8E%20%D0%BA%D0%BE%D0%BD%D1%81%D1%83%D0%BB%D1%8C%D1%82%D0%B0%D1%86%D0%B8%D1%8E"
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "Я вижу, что вы ещё не успели оформить курс.\n\n"
                "Если есть сомнения или вопросы — приглашаю на личную консультацию.\n\n"
                "Разберём, как именно вам развивать интуицию, и отвечу на любые вопросы 🙏"
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📅 Записаться на консультацию", url=diag_url),
            ]]),
        )
    except Exception as exc:
        logger.warning("No-payment reminder failed: %s", exc)


# ══════════════════════════════════════════════════════════════════════════════
# ПРОДЛЕНИЕ (29 дней)
# ══════════════════════════════════════════════════════════════════════════════
async def delayed_renewal_reminder(bot, chat_id: int, user_id: int):
    await asyncio.sleep(29 * 24 * 60 * 60)
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "⏰ Завтра заканчивается доступ к курсу «Основы управления интуицией».\n\n"
                "Вы можете продлить доступ ещё на месяц за *990 ₽*.\n\n"
                "Нажмите кнопку ниже, чтобы продлить 👇"
            ),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Продлить за 990 ₽", callback_data="renew_course"),
            ]]),
        )
    except Exception as exc:
        logger.warning("Renewal reminder failed: %s", exc)


async def renew_course_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    receipt_data = json.dumps({
        "receipt": {
            "items": [{
                "description": "Продление доступа к курсу «Основы управления интуицией»",
                "quantity": 1,
                "amount": {"value": "990.00", "currency": "RUB"},
                "vat_code": 1,
                "payment_mode": "full_payment",
                "payment_subject": "service",
            }],
            "tax_system_code": 2,
        }
    }, ensure_ascii=False)
    try:
        await context.bot.send_invoice(
            chat_id=q.message.chat_id,
            title="Продление курса «Основы управления интуицией»",
            description="Продление доступа на 1 месяц",
            payload="course_renewal_990",
            provider_token=YOOKASSA_TOKEN,
            currency="RUB",
            prices=[LabeledPrice("Продление доступа", 99000)],
            need_name=True,
            need_email=True,
            send_email_to_provider=True,
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text="Не удалось открыть оплату. Попробуйте ещё раз или напишите нам.",
        )


# ══════════════════════════════════════════════════════════════════════════════
# ЗАПУСК
# ══════════════════════════════════════════════════════════════════════════════
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(choice_callback,    pattern="^c[1-6]$"))
    app.add_handler(CallbackQueryHandler(spec_offer_callback, pattern="^spec_offer$"))
    app.add_handler(CallbackQueryHandler(buy_course_callback, pattern="^buy_course$"))
    app.add_handler(CallbackQueryHandler(pay_now_callback,    pattern="^pay_now$"))
    app.add_handler(CallbackQueryHandler(renew_course_callback, pattern="^renew_course$"))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    logger.info("Podarok bot запущен ✓")
    app.run_polling()


if __name__ == "__main__":
    main()
