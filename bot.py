import asyncio
import logging
import random
import time

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "ТВОЙ_ТОКЕН"

import os

token = os.getenv("BOT_TOKEN")

print("RAW:", repr(token))
print("LEN:", len(token) if token else None)
print("HAS_COLON:", ":" in token if token else None)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

# ===== STATES =====
class S(StatesGroup):
    city = State()
    product = State()
    district = State()
    payment = State()

# ===== ГОРОДА (ВСТАВЬ СВОИ 300 ПОЛНОСТЬЮ) =====
ALL_CITIES = [
    "Москва","Санкт-Петербург","Новосибирск","Екатеринбург","Казань",
    "Нижний Новгород","Челябинск","Омск","Самара","Ростов-на-Дону",
    "Уфа","Красноярск","Воронеж","Пермь","Волгоград",
    # 👉 ВСТАВЬ ОСТАЛЬНЫЕ 300 ГОРОДОВ СЮДА
]

# ===== 50 ГОРОДОВ С РАЙОНАМИ =====
LOCATIONS = {
    "Москва": ["Тверской","Арбат","Хамовники","Пресненский","Басманный"],
    "Санкт-Петербург": ["Центральный","Адмиралтейский","Петроградский","Выборгский","Василеостровский"],
    "Новосибирск": ["Центральный","Ленинский","Октябрьский","Советский","Калининский"],
    "Екатеринбург": ["Ленинский","Кировский","Чкаловский","Железнодорожный","Октябрьский"],
    "Казань": ["Вахитовский","Советский","Московский","Кировский","Приволжский"],
    "Нижний Новгород": ["Нижегородский","Советский","Автозаводский","Сормовский","Канавинский"],
    "Челябинск": ["Центральный","Калининский","Курчатовский","Советский","Металлургический"],
    "Омск": ["Центральный","Советский","Кировский","Ленинский","Октябрьский"],
    "Самара": ["Ленинский","Октябрьский","Промышленный","Советский","Куйбышевский"],
    "Ростов-на-Дону": ["Ленинский","Кировский","Советский","Ворошиловский","Октябрьский"],
    "Уфа": ["Советский","Кировский","Октябрьский","Ленинский","Калининский"],
    "Красноярск": ["Центральный","Советский","Свердловский","Железнодорожный","Кировский"],
    "Воронеж": ["Центральный","Коминтерновский","Советский","Левобережный","Железнодорожный"],
    "Пермь": ["Ленинский","Свердловский","Индустриальный","Мотовилихинский","Орджоникидзевский"],
    "Волгоград": ["Центральный","Дзержинский","Краснооктябрьский","Ворошиловский","Тракторозаводский"],
    # 👉 можешь добавить до 50
}

# ===== ТОВАРЫ =====
PRODUCTS = {
    "Футболка": 1200,
    "Кроссовки": 3500,
    "Толстовка": 2500,
    "Плед": 1800,
    "Шарф": 900
}

# ===== КОШЕЛЬКИ =====
BTC = "bc1qexamplewallet"
USDT = "TXexamplewallet"
TON = "UQexamplewallet"

# ===== КУРСЫ (пример) =====
BTC_RATE = 6000000
USDT_RATE = 100
TON_RATE = 300

# ===== UI =====
def menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏙 Выбрать город", callback_data="menu_city")]
    ])

def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")]
    ])

# ===== START =====
@dp.message()
async def start(message: types.Message):
    await message.answer("Добро пожаловать", reply_markup=menu_kb())

# ===== MENU =====
@dp.callback_query(lambda c: c.data == "menu")
async def menu(callback: types.CallbackQuery):
    await callback.message.edit_text("Главное меню", reply_markup=menu_kb())

# ===== ГОРОДА =====
@dp.callback_query(lambda c: c.data == "menu_city")
async def city(callback: types.CallbackQuery):
    first = ALL_CITIES[:15]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=c, callback_data=f"city_{c}")]
        for c in first
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🌍 Другой город", callback_data="other")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])

    await callback.message.edit_text("Выбери город", reply_markup=kb)

@dp.callback_query(lambda c: c.data == "other")
async def other(callback: types.CallbackQuery):
    await callback.message.edit_text("Введи город текстом")

@dp.message()
async def manual_city(message: types.Message, state: FSMContext):
    if message.text not in ALL_CITIES:
        return await message.answer("❌ Неверный город")

    await state.update_data(city=message.text)
    await show_products(message, state)

@dp.callback_query(lambda c: c.data.startswith("city_"))
async def select_city(callback: types.CallbackQuery, state: FSMContext):
    city = callback.data.replace("city_", "")
    await state.update_data(city=city)
    await show_products(callback.message, state)

# ===== ТОВАРЫ =====
async def show_products(message, state):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=p, callback_data=f"prod_{p}")]
        for p in PRODUCTS
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="menu_city")])

    await message.edit_text("Выбери товар", reply_markup=kb)

# ===== ТОВАР =====
@dp.callback_query(lambda c: c.data.startswith("prod_"))
async def product(callback: types.CallbackQuery, state: FSMContext):
    product = callback.data.replace("prod_", "")
    data = await state.get_data()
    city = data["city"]

    await state.update_data(product=product)

    if city in LOCATIONS:
        districts = LOCATIONS[city]
    else:
        districts = ["Центр","Вокзал","Рынок","Север","Юг"]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=d, callback_data=f"dist_{d}")]
        for d in districts[:5]
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="menu_city")])

    await callback.message.edit_text(f"{city}\nВыбери район", reply_markup=kb)

# ===== РАЙОН =====
@dp.callback_query(lambda c: c.data.startswith("dist_"))
async def district(callback: types.CallbackQuery, state: FSMContext):
    d = callback.data.replace("dist_", "")
    data = await state.get_data()

    price = PRODUCTS[data["product"]]

    await state.update_data(district=d, price=price, time=time.time())

    await show_payment(callback.message, state)

# ===== ОПЛАТА =====
async def show_payment(message, state):
    data = await state.get_data()
    price = data["price"]

    btc = round(price / BTC_RATE, 6)
    usdt = round(price / USDT_RATE, 2)
    ton = round(price / TON_RATE, 2)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")]
    ])

    await message.edit_text(
        f"💰 Оплата\n\n"
        f"{price} ₽\n\n"
        f"BTC: <code>{BTC}</code>\n{btc}\n\n"
        f"USDT: <code>{USDT}</code>\n{usdt}\n\n"
        f"TON: <code>{TON}</code>\n{ton}\n\n"
        f"⏳ 15 минут на оплату",
        reply_markup=kb
    )

# ===== ПРОВЕРКА =====
@dp.callback_query(lambda c: c.data == "check")
async def check(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if time.time() - data["time"] > 900:
        return await callback.answer("Время вышло", show_alert=True)

    await callback.answer("Платёж не найден", show_alert=True)

# ===== RUN =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())