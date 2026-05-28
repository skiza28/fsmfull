import asyncio
import json
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
import string
import re

load_dotenv()

TOKEN = os.getenv("TOKEN")

ADMIN_ID = os.getenv("ADMIN_ID")

ANKETAS_FILE = "anketas.json"

class Form(StatesGroup):
    name = State()
    age = State()
    phone = State()





def read_an():
    if os.path.exists(ANKETAS_FILE):
        with open(ANKETAS_FILE, "r", encoding="utf-8" ) as f:
            return json.load(f)
    return {}


def save_an(user_id: int, user_data: dict):
    # ЕСЛИ СУЩЕСТВУЕТ СЛОВАРЬ, ТО РАВНЯЕТСЯ
    anketas = read_an()
    user_id_str = str(user_id)
    # ОПРЕДЕЛЯЕТ ВРЕМЯ И ЗАПИСЫВАЕТ ВСЕ В КЛЮЧ
    user_data["write"] = datetime.now().isoformat()
    # ЗАПИСЬ ВРЕМЕНИ В СЛОВАРЬ И В КЛЮЧ USER_ID_STR (1234558)
    anketas[user_id_str] = user_data
    # СОХРАНЕНИЕ В JSON ФАЙЛ
    with open(ANKETAS_FILE, "w", encoding='utf-8') as f:
        json.dump(anketas, f, ensure_ascii=False, indent=4)
        # СОХРАНЯЕТ СЛОВАРЬ anketas В JSON


# ПОИСК АНКЕТЫ ПОЛЬЗОВАТЕЛЯ ПО ID
def get_user(user_id: int):
    anketas = read_an()
    user_id_str = str(user_id)
    return anketas.get(user_id_str)                        # для эксперимента

async def send_admin(bot, user_data, user_id, username=None):
    message_text = (
        f'*Новая анкета!*\n\n'
        f'📑Информация о пользователе:\n'
        f'ID: {user_id}\n'
        f'Время заполнения: {datetime.now().strftime('%H:%M %d.%m.%Y')}\n\n'
        f'Ответы на вопросы:\n'
        f"Имя: {user_data.get('name', '-')}\n"
        f"Телефон: {user_data.get('phone', '-')}\n"
        f"Возраст: {user_data.get('age', '-')}\n"
    )
    await bot.send_message(chat_id=ADMIN_ID, text=message_text, parse_mode=ParseMode.MARKDOWN)

async def register_an(dp):

    @dp.message(Command('start'))
    async def cmd_start(message: types.Message, state: FSMContext):
        # /clear удаляет только состояния, json не трогает

        # проверяет есть ли у user_id анкета
        existing = get_user(message.from_user.id)

        # ЕСЛИ СЛОВАРЬ НЕ ПУСТОЙ
        if existing:
            await message.answer(
                f"*Твоя анкета уже готова!*\n\n"
                f"Имя: {existing.get('name', '-')}\n"
                f"Телефон: {existing.get('phone', '-')}\n"
                f"Город: {existing.get('city', '-')}\n\n"
                f"Чтобы начать новую анкету, напиши /new",
                parse_mode=ParseMode.MARKDOWN
            )
        # ИНАЧЕ
        else:
            await message.answer(
                f'*Привет, я бот-анкета.*✨\n\n'
                f'Я задам несколько вопросов.\n'
                f'Для отмены используй /cancel\n\n'
                f'Как тебя зовут?',
                parse_mode=ParseMode.MARKDOWN
            )

            await state.set_state(Form.name)


# СОДАНИЕ НОВОЙ АНКЕТЫ
    @dp.message(Command('new'))
    async def cmd_new(message: types.Message, state: FSMContext):
            # СТИРАЕТ СОСТОЯНИЯ И НАЧИНАЕТ С НУЛЯ
            await state.clear()
            await message.answer(
                f'Новая анкета.✅\n\n'
                f'Как тебя зовут?'
            )
            await state.set_state(Form.name)


    @dp.message(Command('cancel'))
    async def cmd_cancel(message: types.Message, state: FSMContext):
        # ПРОВЕРЯЕТ НА КАКОМ ШАГЕ ПОЛЬЗОВАТЕЛЬ
        current_st = await state.get_state()
        # ЕСЛИ ПОЛЬЗОВАТЕЛЬ НЕ НАЧАНАЛ АНКЕТУ
        if current_st is None:
            await message.answer("❌Ты не заполняешь анкету, напиши /start")
            return
        await state.clear()
        await message.answer(
            f'❌Анкетирование отменено\n'
            f'Чтобы начать заново, напишите /start'
        )


    @dp.message(Form.name, F.text)
    async def st_name(message: types.Message, state: FSMContext):
        text = message.text.strip()
        if len(text) < 2:
            await message.answer("❌Ваше имя слишком короткое.\nВведите еще раз:")
            return
        if any(char in string.punctuation for char in text):
            await message.answer("❌Введите имя буквами")
            return
        if any(char.isdigit() for char in text):
            await message.answer("❌Нужно ввести имя буквами")
            return
        await state.update_data(name=text)
        await message.answer("Сколько тебе лет?")
        await state.set_state(Form.age)

    @dp.message(Form.age, F.text)
    async def st_age(message: types.Message, state: FSMContext):
        age_text = message.text.strip()
        if not age_text.isdigit():
            await message.answer("❌Нужно ввести возраст цифрами")
            return
        age = int(age_text)

        if age < 1 or age > 120:
            await message.answer("❌Введите свой настоящий возраст")
            return
        await state.update_data(age=age)
        await message.answer("Какой у вас номер телефона?")
        await state.set_state(Form.phone)

    @dp.message(Form.phone, F.text)
    async def st_phone(message: types.Message, state: FSMContext):
        phone = message.text.strip()
        # УДАЛЯЕТ СКОКИ, ПРОБЕЛЫ, ДЕФИСЫ В ТЕКСТЕ
        clean_phone = re.sub(r'[\s\(\)\-]', '', phone)
        # ПРОВЕРЯЕТ ПРАВИЛЬНЫЙ ЛИ НОМЕР
        if not re.match(r'^\+\d{10,15}$', clean_phone):
            await message.answer("❌Неверный формат телефона!\n"
                                 "Пример +7/+89044569875\n"
                                 "Введите заново")
            return
        await state.update_data(phone=phone)
        user_data = await state.get_data()
        save_an(message.from_user.id, user_data)
        await send_admin(
            bot=message.bot,
            user_id=message.from_user.id,
            user_data=user_data,
        )

        await message.answer(
            f"✨*Спасибо за заполнение анкеты!*\n"
            f"Вот твоя анкета:\n\n"
            f"Имя: {user_data.get('name')}\n"
            f"Возраст: {user_data.get('age')}\n"
            f"Телефон: {user_data.get('phone', '-')}\n"
            f"Чтобы начать заново нажмите /new",
            parse_mode=ParseMode.MARKDOWN
        )
        await state.clear()

    @dp.message()
    async def random(message: types.Message, state: FSMContext):
        current_state = await state.get_state()
        if current_state is None:
            await message.answer(
                "Привет, я бот анкета. Я понимаю только эти команды:\n"
                "/start - начать анкету\n"
                "/new - новая анкета\n"
                "/cancel - отменить анкету"
            )


async def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                        )
    bot = Bot(token=TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    await register_an(dp)

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())



