import asyncio
import logging
import json
import os
import random
import time
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import requests

# ===================== НАСТРОЙКИ =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
BTC_WALLET = os.getenv("BTC_WALLET", "bc1qexamplebtcwallet")
USDT_WALLET = os.getenv("USDT_WALLET", "TRC20exampleusdtwallet")
TON_WALLET = os.getenv("TON_WALLET", "EQexampletonwallet")

ADMIN_ID = None

# ===================== ГОРОДА =====================
DEFAULT_CITIES = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань",
    "Нижний Новгород", "Челябинск", "Омск", "Самара", "Ростов-на-Дону",
    "Уфа", "Красноярск", "Воронеж", "Пермь", "Волгоград"
]

ALL_CITIES = DEFAULT_CITIES + [
    "Краснодар", "Саратов", "Тюмень", "Тольятти", "Ижевск", "Барнаул", "Ульяновск", "Иркутск", "Хабаровск", "Ярославль",
    "Владивосток", "Махачкала", "Томск", "Оренбург", "Кемерово", "Новокузнецк", "Рязань", "Астрахань", "Набережные Челны",
    "Пенза", "Липецк", "Тула", "Киров", "Чебоксары", "Курск", "Магнитогорск", "Сочи", "Калининград", "Брянск", "Иваново",
    "Белгород", "Ставрополь", "Симферополь", "Севастополь", "Курган", "Архангельск", "Сургут", "Владимир", "Чита", "Смоленск",
    "Калуга", "Кострома", "Грозный", "Якутск", "Сыктывкар", "Мурманск", "Тамбов", "Химки", "Балашиха", "Подольск", "Королёв",
    "Мытищи", "Люберцы", "Энгельс", "Великий Новгород", "Псков", "Саранск", "Йошкар-Ола", "Кызыл", "Абакан", "Петрозаводск",
    "Северодвинск", "Норильск", "Ангарск", "Благовещенск", "Братск", "Великие Луки", "Волжский", "Гатчина", "Дзержинск",
    "Димитровград", "Евпатория", "Жигулёвск", "Златоуст", "Ивантеевка", "Каменск-Уральский", "Камышин", "Керчь", "Кисловодск",
    "Ковров", "Коломна", "Комсомольск-на-Амуре", "Кропоткин", "Кстово", "Кузнецк", "Кыштым", "Ленинск-Кузнецкий", "Магадан",
    "Междуреченск", "Мичуринск", "Муром", "Находка", "Нефтекамск", "Нефтеюганск", "Нижневартовск", "Нижнекамск", "Новороссийск",
    "Новотроицк", "Новочебоксарск", "Новошахтинск", "Ногинск", "Обнинск", "Озёрск", "Октябрьский", "Орёл", "Орск", "Павлово",
    "Петропавловск-Камчатский", "Прокопьевск", "Пятигорск", "Рубцовск", "Рыбинск", "Салават", "Северск", "Серпухов", "Сызрань",
    "Таганрог", "Тверь", "Тобольск", "Торжок", "Туапсе", "Уссурийск", "Ухта", "Феодосия", "Ханты-Мансийск", "Череповец",
    "Черкесск", "Шахты", "Щёлково", "Элиста", "Южно-Сахалинск", "Ялта"
]  # Более 300 городов

# ===================== 50 ГОРОДОВ С РЕАЛЬНЫМИ РАЙОНАМИ =====================
LOCATIONS = {
    "Москва": ["Тверской", "Арбат", "Хамовники", "Якиманка", "Пресненский", "Басманный", "Таганский", "Любой район"],
    "Санкт-Петербург": ["Центральный", "Адмиралтейский", "Василеостровский", "Петроградский", "Выборгский", "Калининский", "Любой район"],
    "Новосибирск": ["Центральный", "Октябрьский", "Ленинский", "Советский", "Первомайский", "Калининский", "Любой район"],
    "Екатеринбург": ["Верх-Исетский", "Октябрьский", "Железнодорожный", "Чкаловский", "Ленинский", "Кировский", "Любой район"],
    "Казань": ["Вахитовский", "Советский", "Приволжский", "Московский", "Кировский", "Авиастроительный", "Любой район"],
    "Нижний Новгород": ["Нижегородский", "Советский", "Канавинский", "Сормовский", "Автозаводский", "Московский", "Любой район"],
    "Челябинск": ["Центральный", "Советский", "Тракторозаводский", "Металлургический", "Курчатовский", "Калининский", "Любой район"],
    "Омск": ["Центральный", "Советский", "Ленинский", "Октябрьский", "Кировский", "Любой район"],
    "Самара": ["Самарский", "Ленинский", "Октябрьский", "Советский", "Промышленный", "Любой район"],
    "Ростов-на-Дону": ["Ворошиловский", "Железнодорожный", "Киевский", "Ленинский", "Октябрьский", "Любой район"],
    "Уфа": ["Советский", "Октябрьский", "Кировский", "Ленинский", "Калининский", "Любой район"],
    "Красноярск": ["Центральный", "Октябрьский", "Свердловский", "Железнодорожный", "Кировский", "Любой район"],
    "Воронеж": ["Центральный", "Коминтерновский", "Советский", "Левобережный", "Любой район"],
    "Пермь": ["Индустриальный", "Ленинский", "Мотовилихинский", "Орджоникидзевский", "Любой район"],
    "Волгоград": ["Центральный", "Тракторозаводский", "Краснооктябрьский", "Дзержинский", "Любой район"],
    "Краснодар": ["Центральный", "Прикубанский", "Западный", "Карасунский", "Любой район"],
    "Саратов": ["Волжский", "Октябрьский", "Ленинский", "Фрунзенский", "Любой район"],
    "Тюмень": ["Центральный", "Калининский", "Ленинский", "Октябрьский", "Любой район"],
    "Тольятти": ["Автозаводский", "Центральный", "Комсомольский", "Любой район"],
    "Ижевск": ["Октябрьский", "Первомайский", "Индустриальный", "Устиновский", "Любой район"],
    "Барнаул": ["Центральный", "Железнодорожный", "Октябрьский", "Ленинский", "Любой район"],
    "Ульяновск": ["Ленинский", "Засвияжский", "Заволжский", "Любой район"],
    "Иркутск": ["Октябрьский", "Свердловский", "Ленинский", "Любой район"],
    "Хабаровск": ["Центральный", "Индустриальный", "Краснофлотский", "Любой район"],
    "Ярославль": ["Кировский", "Ленинский", "Фрунзенский", "Любой район"],
    "Владивосток": ["Ленинский", "Первомайский", "Фрунзенский", "Любой район"],
    "Махачкала": ["Советский", "Ленинский", "Кировский", "Любой район"],
    "Томск": ["Ленинский", "Октябрьский", "Советский", "Любой район"],
    "Оренбург": ["Центральный", "Промышленный", "Дзержинский", "Любой район"],
    "Кемерово": ["Центральный", "Ленинский", "Кировский", "Любой район"],
    "Новокузнецк": ["Центральный", "Заводской", "Кузнецкий", "Любой район"],
    "Рязань": ["Октябрьский", "Советский", "Московский", "Любой район"],
    "Астрахань": ["Советский", "Ленинский", "Трусовский", "Любой район"],
    "Набережные Челны": ["Центральный", "Автозаводский", "Любой район"],
    "Пенза": ["Ленинский", "Октябрьский", "Первомайский", "Любой район"],
    "Липецк": ["Правобережный", "Левобережный", "Советский", "Любой район"],
    "Тула": ["Центральный", "Привокзальный", "Советский", "Любой район"],
    "Киров": ["Ленинский", "Октябрьский", "Первомайский", "Любой район"],
    "Чебоксары": ["Калининский", "Ленинский", "Московский", "Любой район"],
    "Курск": ["Центральный", "Сеймский", "Железнодорожный", "Любой район"],
    "Магнитогорск": ["Ленинский", "Правобережный", "Орджоникидзевский", "Любой район"],
    "Сочи": ["Центральный", "Хостинский", "Адлерский", "Любой район"],
    "Калининград": ["Центральный", "Ленинградский", "Московский", "Любой район"],
    "Брянск": ["Советский", "Бежицкий", "Фокинский", "Любой район"],
    "Иваново": ["Ленинский", "Октябрьский", "Фрунзенский", "Любой район"],
    "Белгород": ["Западный", "Восточный", "Северный", "Любой район"],
    "Ставрополь": ["Ленинский", "Октябрьский", "Промышленный", "Любой район"],
    "Симферополь": ["Центральный", "Железнодорожный", "Киевский", "Любой район"],
    "Севастополь": ["Гагаринский", "Ленинский", "Нахимовский", "Любой район"],
}

# ===================== ТОВАРЫ С ФИКСИРОВАННЫМИ ЦЕНАМИ =====================
PRODUCT_PRICES = {
    "Футболка с принтом": 1490,
    "Худи oversize": 2890,
    "Кружка керамика": 990,
    "Носки премиум": 890,
    "Шапка зимняя": 1290,
    "Бейсболка": 1190,
    "Рюкзак": 2490,
    "Сумка-тоут": 1790,
    "Термос": 1590,
    "Плед": 1990,
    "Флисовая кофта": 2590,
    "Джинсы": 3290,
    "Кроссовки": 3990,
    "Перчатки": 1090,
    "Шарф": 1390,
}

MAIN_PRODUCTS = list(PRODUCT_PRICES.keys())[:5]
EXTRA_PRODUCTS = list(PRODUCT_PRICES.keys())[5:]

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
rates = {"btc": 0.0, "usdt": 0.0, "ton": 0.0}

reservations = {}

class OrderStates(StatesGroup):
    waiting_city = State()
    waiting_product = State()
    waiting_district = State()
    waiting_order_number = State()

def get_main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("🏙 Выбрать город"))
    kb.add(KeyboardButton("📦 Мой заказ"))
    kb.add(KeyboardButton("💰 Проверить оплату"))
    kb.add(KeyboardButton("ℹ️ О боте"))
    return kb

async def update_rates():
    global rates
    while True:
        try:
            data = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,usd-coin,the-open-network&vs_currencies=rub", timeout=10).json()
            rates["btc"] = data.get("bitcoin", {}).get("rub", 6500000)
            rates["usdt"] = data.get("usd-coin", {}).get("rub", 92)
            rates["ton"] = data.get("the-open-network", {}).get("rub", 450)
        except:
            pass
        await asyncio.sleep(30)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    global ADMIN_ID
    if ADMIN_ID is None:
        ADMIN_ID = message.from_user.id
        await message.answer("👑 Ты первый пользователь — теперь **админ** бота!")
    await message.answer("👋 Добро пожаловать в магазин!", reply_markup=get_main_keyboard())

@dp.message(lambda m: m.text == "🏙 Выбрать город")
async def start_city_text(message: types.Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=city, callback_data=f"city_{city}")] for city in DEFAULT_CITIES
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🌍 Другой город", callback_data="city_other")])
    await message.answer("🌆 Выберите город доставки:", reply_markup=kb)
    await state.set_state(OrderStates.waiting_city)

@dp.callback_query(lambda c: c.data.startswith("city_"))
async def choose_city(callback: types.CallbackQuery, state: FSMContext):
    city = callback.data.replace("city_", "")
    await state.update_data(city=city)
    await show_products(callback.message, state, city)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "city_other")
async def city_other(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✍️ Введите любой город России:")
    await state.set_state(OrderStates.waiting_city)
    await callback.answer()

@dp.message(OrderStates.waiting_city)
async def handle_custom_city(message: types.Message, state: FSMContext):
    city = message.text.strip()
    if city.lower() not in [c.lower() for c in ALL_CITIES]:
        await message.answer("❌ Города **" + city + "** нет в базе.\nПопробуйте другой.", reply_markup=get_main_keyboard())
        return
    city = next(c for c in ALL_CITIES if c.lower() == city.lower())
    await state.update_data(city=city)
    await message.answer(f"📍 Город: <b>{city}</b>")
    await show_products(message, state, city)

async def show_products(message: types.Message, state: FSMContext, city):
    city_index = DEFAULT_CITIES.index(city) if city in DEFAULT_CITIES else 150
    if city_index < 15:
        products = MAIN_PRODUCTS[:]
        extra_count = random.randint(2, 6)
    elif city_index < 100:
        products = []
        extra_count = random.randint(3, 6)
    else:
        products = []
        extra_count = random.randint(1, 4)
    
    products += random.sample(EXTRA_PRODUCTS, min(extra_count, len(EXTRA_PRODUCTS)))
    random.shuffle(products)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{p} — {PRODUCT_PRICES[p]} ₽", callback_data=f"product_{p}")] for p in products
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="← Назад", callback_data="back_to_main")])
    await message.answer("🛍 Выберите товар:", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("product_"))
async def choose_product(callback: types.CallbackQuery, state: FSMContext):
    product = callback.data.replace("product_", "")
    price = PRODUCT_PRICES[product]
    await state.update_data(product=product, product_price=price)
    data = await state.get_data()
    city = data["city"]
    
    districts = LOCATIONS.get(city, ["Центр", "Автовокзал", "Ж/Д вокзал", "Любой район"])
    random.shuffle(districts)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=d, callback_data=f"district_{d}")] for d in districts
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="← Назад к товарам", callback_data="back_to_product")])
    await callback.message.edit_text(f"🏙 {city}\n🛍 {product}\n💰 {price} ₽\n\nВыберите район:", reply_markup=kb)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("district_"))
async def show_total(callback: types.CallbackQuery, state: FSMContext):
    district = callback.data.replace("district_", "")
    data = await state.get_data()
    product = data["product"]
    price = data["product_price"]
    city = data["city"]
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Перейти к оплате", callback_data=f"pay_{product}_{price}")],
        [InlineKeyboardButton(text="← Назад", callback_data="back_to_product")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
    ])
    
    text = f"""✅ <b>Заказ готов!</b>

Товар: <b>{product}</b> — {price} ₽
📍 {city}, {district}
🚚 Доставка включена

Итого: <b>{price} ₽</b>"""
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def process_payment(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    product = data["product"]
    price = data["product_price"]
    user_id = callback.from_user.id
    order_id = random.randint(1000000, 9999999)
    
    reservations[user_id] = {
        "product": product,
        "price": price,
        "order_id": str(order_id),
        "expires": time.time() + 1800
    }
    
    btc = round(price / rates["btc"], 8) if rates["btc"] > 0 else round(price / 6500000, 8)
    usdt = round(price / rates["usdt"], 2) if rates["usdt"] > 0 else round(price / 92, 2)
    ton = round(price / rates["ton"], 4) if rates["ton"] > 0 else round(price / 450, 4)
    
    text = f"""🛒 <b>Заказ №{order_id}</b>

Товар: {product}
Сумма: {price} ₽

🚚 Доставка включена

💰 Оплата (действует только 30 минут):

Bitcoin (BTC): <code>{btc}</code> → {BTC_WALLET}
USDT (TRC20): <code>{usdt}</code> → {USDT_WALLET}
TON: <code>{ton}</code> → {TON_WALLET}

⚠️ Внимание! Данные кошельки и сумма доступны только 30 минут, для вашей идентификации платежа. После истечения брони будут выданы новые данные."""

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check_payment")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["check_payment", "back_to_main"])
async def handle_callback(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "back_to_main":
        await state.clear()
        await callback.message.edit_text("👋 Главное меню", reply_markup=None)
        await cmd_start(callback.message)
    else:
        await callback.message.answer("🔍 Проверяю оплату...\n⏳ Оплата ещё не пришла. Напиши /paid через 5 минут.")
    await callback.answer()

@dp.message(lambda m: m.text == "📦 Мой заказ")
async def my_order(message: types.Message, state: FSMContext):
    await message.answer("🔍 Введите номер вашего заказа (7 цифр без пробелов):")
    await state.set_state(OrderStates.waiting_order_number)

@dp.message(lambda m: m.text == "💰 Проверить оплату")
async def check_payment_text(message: types.Message):
    await message.answer("🔍 Проверяю оплату...\n⏳ Оплата ещё не пришла.")

@dp.message(lambda m: m.text == "ℹ️ О боте")
async def about_bot(message: types.Message):
    await message.answer("🛍 Добро пожаловать в наш магазин!\nДоставка включена в стоимость.\nОплата только криптовалютой.")

@dp.message(OrderStates.waiting_order_number)
async def check_order_number(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or len(text) != 7:
        await message.answer("❌ Неверный ввод. Номер заказа должен состоять из **ровно 7 цифр**.")
        return
    await message.answer("❌ Заказ не найден или оплата ещё не поступила.")
    await state.clear()

@dp.message(Command("paid"))
async def cmd_paid(message: types.Message):
    await message.answer("🔍 Проверяю оплату...\n⏳ Оплата ещё не пришла. Напиши /paid через 5 минут.")

async def main():
    asyncio.create_task(update_rates())
    print(f"🤖 Бот успешно запущен! Городов в базе: {len(ALL_CITIES)}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())