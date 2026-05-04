import asyncio
import logging
import time
import os

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

# ===== TOKEN (Railway) =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is empty! Check Railway Variables")

# ===== BOT =====
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher(storage=MemoryStorage())

# ===== FSM =====
class S(StatesGroup):
    city = State()
    product = State()
    district = State()
    payment = State()

# ===== 300 ГОРОДОВ =====
ALL_CITIES = [
    "Москва","Санкт-Петербург","Новосибирск","Екатеринбург","Казань",
    "Нижний Новгород","Челябинск","Самара","Омск","Ростов-на-Дону",
    "Уфа","Красноярск","Воронеж","Пермь","Волгоград","Краснодар",
    "Саратов","Тюмень","Тольятти","Ижевск","Барнаул","Ульяновск",
    "Иркутск","Хабаровск","Ярославль","Владивосток","Махачкала",
    "Томск","Оренбург","Кемерово","Новокузнецк","Рязань","Астрахань",
    "Пенза","Липецк","Киров","Чебоксары","Тула","Калининград",
    "Брянск","Курск","Иваново","Магнитогорск","Тверь","Сочи",
    "Сургут","Белгород","Архангельск","Владимир","Ставрополь",
    "Нижний Тагил","Калуга","Смоленск","Чита","Орёл","Волжский",
    "Череповец","Владикавказ","Мурманск","Саранск","Якутск",
    "Грозный","Кострома","Петрозаводск","Йошкар-Ола","Новороссийск",
    "Тамбов","Благовещенск","Псков","Бийск","Петропавловск-Камчатский",
    "Курган","Нальчик","Энгельс","Рыбинск","Симферополь",
    "Севастополь","Дербент","Армавир","Нефтеюганск","Прокопьевск",
    "Абакан","Одинцово","Мытищи","Химки","Королёв","Подольск",
    "Люберцы","Красногорск","Балашиха","Коломна","Орск",
    "Старый Оскол","Златоуст","Норильск","Альметьевск","Элиста",
    # ... (итого ~300 городов — список сокращён для читаемости)
]

# ===== 50 ГОРОДОВ С РАЙОНАМИ =====
LOCATIONS = {
    "Москва": ["Центральный","Северный","Южный","Восточный","Западный"],
    "Санкт-Петербург": ["Центральный","Адмиралтейский","Петроградский","Выборгский","Московский"],
    "Новосибирск": ["Центральный","Ленинский","Советский","Октябрьский","Калининский"],
    "Екатеринбург": ["Ленинский","Кировский","Чкаловский","Октябрьский","Железнодорожный"],
    "Казань": ["Вахитовский","Советский","Московский","Кировский","Приволжский"],
    "Нижний Новгород": ["Нижегородский","Автозаводский","Сормовский","Советский","Канавинский"],
    "Челябинск": ["Центральный","Калининский","Курчатовский","Советский","Металлургический"],
    "Самара": ["Ленинский","Октябрьский","Промышленный","Кировский","Советский"],
    "Омск": ["Центральный","Советский","Кировский","Ленинский","Октябрьский"],
    "Ростов-на-Дону": ["Ленинский","Кировский","Октябрьский","Советский","Ворошиловский"],
    # ... можно расширить до 50 (структура готова)
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
BTC = "bc1qexample"
USDT = "TRCexample"
TON = "UQexample"

BTC_RATE = 6000000
USDT_RATE = 100
TON_RATE = 300

# ===== UI =====
def menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏙 Выбрать город", callback_data="menu_city")]
    ])

# ===== START =====
@dp.message()
async def start(message: types.Message):
    await message.answer("Добро пожаловать", reply_markup=menu_kb())

# ===== CITY MENU =====
@dp.callback_query(lambda c: c.data == "menu_city")
async def city_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=c, callback_data=f"city_{c}")]
        for c in ALL_CITIES[:15]
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🌍 Ввести город", callback_data="manual")])

    await callback.message.edit_text("Выберите город", reply_markup=kb)

@dp.callback_query(lambda c: c.data == "manual")
async def manual(callback: types.CallbackQuery):
    await callback.message.edit_text("Введите город текстом")

@dp.message()
async def manual_city(message: types.Message, state: FSMContext):
    if message.text not in ALL_CITIES:
        return await message.answer("❌ Город не найден")

    await state.update_data(city=message.text)
    await show_products(message)

@dp.callback_query(lambda c: c.data.startswith("city_"))
async def select_city(callback: types.CallbackQuery, state: FSMContext):
    city = callback.data.replace("city_", "")
    await state.update_data(city=city)
    await show_products(callback.message)

# ===== PRODUCTS =====
async def show_products(message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=p, callback_data=f"prod_{p}")]
        for p in PRODUCTS
    ])

    await message.edit_text("Выберите товар", reply_markup=kb)

# ===== PRODUCT =====
@dp.callback_query(lambda c: c.data.startswith("prod_"))
async def product(callback: types.CallbackQuery, state: FSMContext):
    product = callback.data.replace("prod_", "")
    await state.update_data(product=product)

    city = (await state.get_data()).get("city", "Москва")

    districts = LOCATIONS.get(city, ["Центр","Север","Юг"])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=d, callback_data=f"dist_{d}")]
        for d in districts
    ])

    await callback.message.edit_text("Выберите район", reply_markup=kb)

# ===== DISTRICT =====
@dp.callback_query(lambda c: c.data.startswith("dist_"))
async def district(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    price = PRODUCTS[data["product"]]
    await state.update_data(price=price, time=time.time())

    btc = round(price / BTC_RATE, 6)
    usdt = round(price / USDT_RATE, 2)
    ton = round(price / TON_RATE, 2)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check")]
    ])

    await callback.message.edit_text(
        f"💰 Оплата\n\n"
        f"{price} ₽\n\n"
        f"BTC: {btc}\nUSDT: {usdt}\nTON: {ton}",
        reply_markup=kb
    )

# ===== CHECK =====
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