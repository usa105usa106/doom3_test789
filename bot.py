import asyncio
import logging
import os
import random
import time

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

logging.basicConfig(level=logging.INFO)

# =====================
# CONFIG
# =====================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

# =====================
# STATES
# =====================

class S(StatesGroup):
    city = State()
    product = State()
    district = State()

# =====================
# DATA
# =====================

PRODUCTS = {
    "Футболка": 1200,
    "Кроссовки": 3500,
    "Худи": 2500,
    "Плед": 1800,
    "Шарф": 900
}

ALL_CITIES = [
    "Москва","Санкт-Петербург","Новосибирск","Екатеринбург","Казань",
    "Нижний Новгород","Челябинск","Омск","Самара","Ростов-на-Дону",
    "Уфа","Красноярск","Воронеж","Пермь","Волгоград",
    "Краснодар","Саратов","Тюмень","Тольятти","Ижевск",
    "Барнаул","Ульяновск","Иркутск","Хабаровск","Ярославль",
    "Владивосток","Махачкала","Томск","Оренбург","Кемерово",
    "Новокузнецк","Рязань","Астрахань","Пенза","Липецк",
    "Киров","Чебоксары","Брянск","Тула","Курск",
    "Ставрополь","Улан-Удэ","Тверь","Магнитогорск","Сочи",
    "Иваново","Белгород","Архангельск","Калининград","Владимир",
    "Смоленск","Калуга","Чита","Грозный","Якутск",
    "Сургут","Нижневартовск","Набережные Челны","Стерлитамак","Орёл",
    "Волжский","Кострома","Петрозаводск","Новороссийск","Йошкар-Ола",
    "Сыктывкар","Нальчик","Абакан","Благовещенск","Дзержинск",
    "Шахты","Энгельс","Балаково","Прокопьевск","Армавир",
    "Псков","Бийск","Рубцовск","Норильск","Северодвинск",
    "Ангарск","Братск","Южно-Сахалинск","Каменск-Уральский","Орск",
    "Златоуст","Элиста","Петропавловск-Камчатский","Нижнекамск","Химки",
    "Королёв","Мытищи","Подольск","Люберцы","Серпухов",
    "Одинцово","Красногорск","Балашиха","Раменское","Жуковский"
]

LOCATIONS = {
    "Москва": ["Тверской", "Арбат", "Хамовники", "Пресненский", "Басманный"],
    "Санкт-Петербург": ["Центральный", "Адмиралтейский", "Петроградский", "Выборгский", "Василеостровский"],
    "Новосибирск": ["Центральный", "Ленинский", "Октябрьский", "Советский", "Калининский"],
    "Екатеринбург": ["Ленинский", "Кировский", "Чкаловский", "Железнодорожный", "Октябрьский"],
    "Казань": ["Вахитовский", "Советский", "Московский", "Кировский", "Приволжский"],
    "Нижний Новгород": ["Нижегородский", "Советский", "Автозаводский", "Сормовский", "Канавинский"],
    "Челябинск": ["Центральный", "Калининский", "Курчатовский", "Советский", "Металлургический"],
    "Самара": ["Ленинский", "Октябрьский", "Промышленный", "Советский", "Куйбышевский"],
    "Омск": ["Центральный", "Советский", "Кировский", "Ленинский", "Октябрьский"],
    "Ростов-на-Дону": ["Ленинский", "Кировский", "Ворошиловский", "Советский", "Октябрьский"],
    "Уфа": ["Советский", "Кировский", "Октябрьский", "Ленинский", "Калининский"],
    "Красноярск": ["Центральный", "Советский", "Свердловский", "Железнодорожный", "Кировский"],
    "Воронеж": ["Центральный", "Коминтерновский", "Советский", "Левобережный", "Железнодорожный"],
    "Пермь": ["Ленинский", "Свердловский", "Индустриальный", "Мотовилихинский", "Орджоникидзевский"],
    "Волгоград": ["Центральный", "Дзержинский", "Краснооктябрьский", "Ворошиловский", "Тракторозаводский"],
    "Саратов": ["Октябрьский", "Фрунзенский", "Кировский", "Ленинский", "Заводской"],
    "Тюмень": ["Центральный", "Калининский", "Ленинский", "Восточный", "Вагайский"],
    "Тольятти": ["Автозаводский", "Центральный", "Комсомольский"],
    "Ижевск": ["Устиновский", "Октябрьский", "Индустриальный", "Первомайский"],
    "Барнаул": ["Центральный", "Индустриальный", "Ленинский", "Октябрьский"],
    "Ульяновск": ["Засвияжский", "Ленинский", "Заволжский"],
    "Иркутск": ["Октябрьский", "Свердловский", "Ленинский", "Правобережный"],
    "Хабаровск": ["Центральный", "Индустриальный", "Железнодорожный", "Кировский"],
    "Ярославль": ["Кировский", "Ленинский", "Дзержинский", "Заволжский"],
    "Владивосток": ["Ленинский", "Первомайский", "Первореченский", "Советский"],
    "Махачкала": ["Советский", "Ленинский", "Кировский"],
    "Томск": ["Кировский", "Советский", "Ленинский"],
    "Оренбург": ["Центральный", "Ленинский", "Дзержинский", "Пролетарский"],
    "Кемерово": ["Центральный", "Ленинский", "Заводский"],
    "Новокузнецк": ["Центральный", "Заводский", "Кузнецкий"],
    "Рязань": ["Советский", "Железнодорожный", "Московский"],
    "Астрахань": ["Кировский", "Ленинский", "Советский"],
    "Пенза": ["Ленинский", "Октябрьский", "Железнодорожный"],
    "Липецк": ["Правобережный", "Советский", "Октябрьский"],
    "Тула": ["Пролетарский", "Центральный", "Зареченский"],
    "Киров": ["Октябрьский", "Ленинский", "Первомайский"],
    "Чебоксары": ["Калининский", "Ленинский", "Московский"],
    "Калининград": ["Ленинградский", "Московский", "Центральный"],
    "Брянск": ["Советский", "Бежицкий", "Фокинский"],
    "Курск": ["Центральный", "Сеймский", "Железнодорожный"],
    "Иваново": ["Ленинский", "Октябрьский", "Фрунзенский"],
    "Магнитогорск": ["Правобережный", "Ленинский", "Орджоникидзевский"],
    "Тверь": ["Центральный", "Заволжский", "Московский"],
    "Ставрополь": ["Ленинский", "Октябрьский", "Промышленный"],
    "Набережные Челны": ["Автозаводский", "Комсомольский", "Центральный"],
    "Белгород": ["Западный", "Восточный", "Центральный"],
    "Сочи": ["Центральный", "Адлерский", "Хостинский"],
    "Архангельск": ["Ломоносовский", "Октябрьский", "Соломбальский"],
    "Владимир": ["Ленинский", "Октябрьский", "Фрунзенский"],
    "Симферополь": ["Центральный", "Киевский", "Железнодорожный"]
}

# WALLETS
BTC_WALLET = "bc1qexample"
USDT_WALLET = "TXexample"
TON_WALLET = "UQexample"

BTC_RATE = 6500000
USDT_RATE = 90
TON_RATE = 320

def get_crypto_amounts(rub: int):
    return round(rub / BTC_RATE, 6), round(rub / USDT_RATE, 2), round(rub / TON_RATE, 3)

# =====================
# KEYBOARDS
# =====================

def main_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="🏙 Выбрать город")],
        [KeyboardButton(text="📦 Мой заказ")],
        [KeyboardButton(text="💰 Проверить оплату")],
        [KeyboardButton(text="ℹ️ О боте")]
    ])

# =====================
# START
# =====================

@dp.message(F.text == "/start")
async def start(m: types.Message):
    await m.answer("🏪 Добро пожаловать в Маркетплейс", reply_markup=main_kb())

# =====================
# MAIN MENU BUTTONS
# =====================

@dp.message(F.text == "🏙 Выбрать город")
async def choose_city_btn(m: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=x, callback_data=f"c_{x}")] for x in ALL_CITIES[:12]
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])
    await m.answer("🏙 Выберите город:", reply_markup=kb)

@dp.message(F.text == "📦 Мой заказ")
async def my_order(m: types.Message):
    await m.answer("📦 У вас пока нет активных заказов.")

@dp.message(F.text == "💰 Проверить оплату")
async def check_payment_btn(m: types.Message):
    await m.answer("💰 У вас нет неоплаченных заказов.")

@dp.message(F.text == "ℹ️ О боте")
async def about(m: types.Message):
    await m.answer("🛒 Это тестовый маркетплейс.\nОплата в крипте.\nКошельки действительны 30 минут.")

# =====================
# INLINE HANDLERS
# =====================

@dp.callback_query(F.data == "menu")
async def menu(c: types.CallbackQuery):
    await c.message.edit_text("🏪 Главное меню", reply_markup=None)
    await c.message.answer("Выберите действие:", reply_markup=main_kb())

# 1. ГОРОД
@dp.callback_query(F.data.startswith("c_"))
async def city_selected(c: types.CallbackQuery, state: FSMContext):
    city = c.data[2:]
    await state.update_data(city=city)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=p, callback_data=f"p_{p}")] for p in PRODUCTS.keys()
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="🔙 Города", callback_data="city"),
        InlineKeyboardButton(text="🏠 Меню", callback_data="menu")
    ])

    await c.message.edit_text(f"📍 Город: <b>{city}</b>\n\n🛍 Выберите товар:", reply_markup=kb)

# 2. ТОВАР
@dp.callback_query(F.data.startswith("p_"))
async def product_selected(c: types.CallbackQuery, state: FSMContext):
    product = c.data[2:]
    await state.update_data(product=product, price=PRODUCTS[product])

    data = await state.get_data()
    city = data['city']
    districts = LOCATIONS.get(city, ["Центр", "Район 1", "Район 2"])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=d, callback_data=f"d_{d}")] for d in districts
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="🔙 Товары", callback_data=f"back_products"),
        InlineKeyboardButton(text="🏠 Меню", callback_data="menu")
    ])

    await c.message.edit_text(f"📍 {city}\n🛍 Товар: <b>{product}</b>\n\nВыберите район:", reply_markup=kb)

# 3. РАЙОН → ОПЛАТА
@dp.callback_query(F.data.startswith("d_"))
async def district_selected(c: types.CallbackQuery, state: FSMContext):
    district = c.data[2:]
    data = await state.get_data()
    
    order_id = random.randint(1000000, 9999999)
    await state.update_data(district=district, order_id=order_id, t=time.time())

    price = data['price']
    product = data['product']
    city = data['city']
    btc, usdt, ton = get_crypto_amounts(price)

    text = (
        f"🆔 <b>Заказ №{order_id}</b>\n\n"
        f"Товар: <b>{product}</b>\n"
        f"Город: <b>{city}</b>\n"
        f"Район: <b>{district}</b>\n\n"
        f"Сумма: <b>{price} ₽</b>\n\n"
        f"🔹 BTC: <code>{btc}</code> → {BTC_WALLET}\n"
        f"🔹 USDT: <code>{usdt}</code> → {USDT_WALLET}\n"
        f"🔹 TON: <code>{ton}</code> → {TON_WALLET}\n\n"
        f"⏰ Кошельки и сумма актуальны 30 минут"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")]
    ])

    await c.message.edit_text(text, reply_markup=kb)

    # Уведомление через 20 минут
    asyncio.create_task(reminder(c.from_user.id, order_id))

async def reminder(user_id: int, order_id: int):
    await asyncio.sleep(20 * 60)  # 20 минут
    try:
        await bot.send_message(
            user_id,
            f"⏳ Заказ №{order_id}\n\nОсталось 10 минут до окончания брони кошельков!"
        )
    except:
        pass

# Проверка оплаты
@dp.callback_query(F.data == "check")
async def check_payment(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if time.time() - data.get("t", 0) > 1800:  # 30 минут
        await c.answer("⛔ Время на оплату вышло (30 минут)", show_alert=True)
        return
    await c.answer("✅ Оплата найдена! Товар в обработке.", show_alert=True)

# =====================
# RUN
# =====================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())