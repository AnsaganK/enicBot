import asyncio
import re

import requests
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from constants import BOT_TOKEN, HOST

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())


class ContactForm(StatesGroup):
    name = State()
    email = State()
    subject = State()
    message = State()


# /start
@dp.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()  # На всякий случай сбрасываем прошлое состояние
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📩 Өтініш жіберу")],
            [KeyboardButton(text="📄 Менің өтініштерім")],
            [KeyboardButton(text="ℹ Ақпарат")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "Сәлем 👋\nENIC.kz байланыс ботына қош келдіңіз!\nНе істегіңіз келеді?",
        reply_markup=kb
    )


@dp.message(F.text == "📩 Өтініш жіберу")
async def handle_application_start(message: Message, state: FSMContext):
    await state.set_state(ContactForm.name)
    await message.answer("Атыңызды енгізіңіз:")


@dp.message(F.text == "ℹ Ақпарат")
async def handle_info(message: Message):
    await message.answer(
        "Бұл бот арқылы сіз ENIC орталығына өтініш, сұрақ немесе хабарлама жібере аласыз.\n\n"
        "Бастау үшін '📩 Өтініш жіберу' батырмасын басыңыз."
    )


@dp.message(F.text == "📄 Менің өтініштерім")
async def list_user_requests(message: Message):
    user_id = message.from_user.id
    url = f'{HOST}/api/contact/messages/{user_id}'
    r = requests.get(url)
    if r.status_code != 200:
        await message.answer("❌ Серверлік қате")
    messages = r.json().get('messages', [])
    if not messages:
        await message.answer(
            "Жіберілген өтініштеріңіз жоқ"
        )
    else:
        text = "<b>📂 Сіздің өтініштеріңіз:</b>\n\n"
        for i, m in enumerate(messages, 1):
            text += (
                f"<b>{i}. {'✅' if m['is_checked'] else '⏺️'} {m['subject']}</b>\n"
                f"<b>{m['created_at']}</b>\n"
                f"---------------------------------------\n"
                f"<i>{m['message'][:100]}</i>...\n"
                f"---------------------------------------\n\n"
            )

        await message.answer(text)


@dp.message(F.text == "/about")
async def about(message: Message):
    await message.answer(
        "ℹ️ <b>ENIC.kz байланыс боты</b>\n\n"
        "Бұл бот арқылы сіз ENIC.KZ орталығына хабарлама жібере аласыз.\n\n"
        "📌 Қол жетімді функциялар:\n"
        "— Байланыс формасын толтыру\n"
        "— Тақырып пен хабарлама жіберу\n"
        "— Жауап күту (электрондық пошта арқылы)\n\n"
        "💡 ENIC-Kazakhstan — білім беру құжаттарын тану, аккредитация және Болон процесі саласында ақпарат беретін ұлттық орталық.\n\n"
        "🌐 Сайт: https://enic.kz"
    )


# 1. Имя
@dp.message(ContactForm.name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Электрондық поштаңызды енгізіңіз:")
    await state.set_state(ContactForm.email)


EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$")


# 2. Email
@dp.message(ContactForm.email)
async def get_email(message: Message, state: FSMContext):
    email = message.text.strip()

    if not EMAIL_REGEX.match(email):
        await message.answer("❌ Электрондық пошта дұрыс емес. Қайтадан енгізіңіз:")
        return  # ❗ НЕ переходим дальше

    await state.update_data(email=email)
    await message.answer("Өтініштің тақырыбын енгізіңіз:")
    await state.set_state(ContactForm.subject)


# 3. Тақырып
@dp.message(ContactForm.subject)
async def get_subject(message: Message, state: FSMContext):
    await state.update_data(subject=message.text)
    await message.answer("Өтініш мазмұнын жазыңыз:")
    await state.set_state(ContactForm.message)


# 4. Хабарлама
@dp.message(ContactForm.message)
async def get_message(message: Message, state: FSMContext):
    await state.update_data(message=message.text)
    data = await state.get_data()

    text = (
        "<b>📬 Жіберілген хабарлама:</b>\n\n"
        f"<b>👤 Аты:</b> {data['name']}\n"
        f"<b>📧 Email:</b> {data['email']}\n"
        f"<b>📝 Тақырып:</b> {data['subject']}\n"
        f"<b>💬 Хабарлама:</b>\n{data['message']}"
    )

    url = f'{HOST}/api/contact/messages/send'
    r = requests.post(url, data={
        'name': data['name'],
        'email': data['email'],
        'subject': data['subject'],
        'message': data['message'],
        'telegram_id': message.from_user.id,
    })
    if r.status_code != 200:
        await message.answer("❌ Серверлік қате")
    else:
        await message.answer(text)
        await message.answer("✅ Өтінішіңіз жіберілді! Рақмет.")
    await state.clear()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
