import asyncio
import logging
import json
import os
import random
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import requests

# ===================== НАСТРОЙКИ =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
BTC_WALLET = os.getenv("BTC_WALLET")
USDT_WALLET = os.getenv("USDT_WALLET")
TON_WALLET = os.getenv("TON_WALLET")

ADMIN_ID = None

FILE_PRODUCTS = "products.json"

DEFAULT_CITIES = ["Москва", "Санкт-Петербург", "Екатеринбург", "Новосибирск", "Краснодар", "Казань"]

LOCATIONS = {
    "Москва": ["Центр (Тверской)", "Север", "Юг", "Восток", "Запад", "Любой район"],
    "Санкт-Петербург": ["Центр", "Василеостровский", "Петроградский", "Выборгский", "Любой район"],
    "Екатеринбург": ["Центр", "Верх-Исетский", "Октябрьский", "Любой район"],
    "Новосибирск": ["Центральный", "Октябрьский", "Ленинский", "Любой район"],
    "Краснодар": ["Центр", "Прикубанский", "Западный", "Любой район"],
    "Казань": ["Центр (Вахитовский)", "Советский", "Приволжский", "Любой район"],
}

MAIN_PRODUCTS = ["Футболка с принтом", "Худи oversize", "Кружка керамика", "Носки премиум", "Шапка зимняя"]
EXTRA_PRODUCTS = ["Бейсболка", "Рюкзак", "Сумка-тоут", "Термос", "Плед", "Флисовая кофта", "Джинсы", "Кроссовки", "Перчатки", "Шарф"]

# =====================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
rates = {"btc": 0.0, "usdt": 0.0, "ton": 0.0}

reservations = {}

class OrderStates(StatesGroup):
    waiting_city = State()
    waiting_product = State()
    waiting_district = State()

def load_products():
    if os.path.exists(FILE_PRODUCTS):
        with open(FILE_PRODUCTS, "r", encoding="utf-8") as f:
            return json.load(f)
    return {p: random.randint(890, 3990) for p in MAIN_PRODUCTS}

PRODUCTS = load_products()

def get_random_stock():
    num = random.randint(3, 20)
    return "более 10" if num > 10 else str(num)

async def update_rates():
    global rates
    while True:
        try:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,usd-coin,the-open-network&vs_currencies=rub"
            data = requests.get(url, timeout=10).json()
            rates["btc"] = data.get("bitcoin", {}).get("rub", 0)
            rates["usdt"] = data.get("usd-coin", {}).get("rub", 92)
            rates["ton"] = data.get("the-open-network", {}).get("rub", 0)
        except:
            pass
        await asyncio.sleep(30)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    global ADMIN_ID
    if ADMIN_ID is None:
        ADMIN_ID = message.from_user.id
        await message.answer("👑 Ты первый пользователь — теперь **админ** бота!")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=city, callback_data=f"city_{city}")] for city in DEFAULT_CITIES
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🌍 Другой город", callback_data="city_other")])
    
    await message.answer("👋 Выбери город доставки:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("city_") and c.data != "city_other")
async def choose_product(callback: types.CallbackQuery, state: FSMContext):
    city = callback.data.replace("city_", "")
    await state.update_data(city=city)
    
    products_to_show = MAIN_PRODUCTS.copy()
    num_extra = random.randint(2, 6)
    extra = random.sample(EXTRA_PRODUCTS, num_extra)
    products_to_show.extend(extra)
    random.shuffle(products_to_show)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"product_{name}")] for name in products_to_show
    ])
    await callback.message.edit_text(f"📍 Город: <b>{city}</b>\nВыбери товар:", reply_markup=keyboard)
    await state.set_state(OrderStates.waiting_product)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "city_other")
async def ask_custom_city(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🌍 Напиши любой город:")
    await state.set_state(OrderStates.waiting_city)

@dp.message(OrderStates.waiting_city)
async def handle_custom_city(message: types.Message, state: FSMContext):
    city = message.text.strip()
    await state.update_data(city=city)
    products_to_show = MAIN_PRODUCTS.copy()
    num_extra = random.randint(2, 6)
    extra = random.sample(EXTRA_PRODUCTS, num_extra)
    products_to_show.extend(extra)
    random.shuffle(products_to_show)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"product_{name}")] for name in products_to_show
    ])
    await message.answer(f"📍 Город: <b>{city}</b>\nВыбери товар:", reply_markup=keyboard)
    await state.set_state(OrderStates.waiting_product)

@dp.callback_query(lambda c: c.data.startswith("product_"))
async def choose_district(callback: types.CallbackQuery, state: FSMContext):
    product_name = callback.data.replace("product_", "")
    price = PRODUCTS.get(product_name, 1990)
    stock = get_random_stock()
    await state.update_data(product=product_name, product_price=price)
    
    data = await state.get_data()
    city = data["city"]
    districts = LOCATIONS.get(city, ["Центр", "Любой район"])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=d, callback_data=f"district_{d}")] for d in districts
    ])
    await callback.message.edit_text(
        f"🎁 <b>{product_name}</b> — {price:,} ₽\n"
        f"📦 В наличии: <b>{stock}</b>\n"
        f"📍 {city}\nВыбери район:",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("district_"))
async def show_total(callback: types.CallbackQuery, state: FSMContext):
    district = callback.data.replace("district_", "")
    data = await state.get_data()
    product_name = data["product"]
    total_rub = data["product_price"]
    city = data["city"]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💳 Перейти к оплате", callback_data=f"pay_{product_name}_{total_rub}")
    ]])
    
    text = (
        f"✅ <b>Заказ готов!</b>\n\n"
        f"Товар: <b>{product_name}</b> — {total_rub:,} ₽\n"
        f"📍 {city}, {district}\n"
        f"🚚 Доставка включена\n"
        f"────────────────\n"
        f"Итого: <b>{total_rub:,} ₽</b>"
    )
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def process_payment(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    parts = callback.data.split("_", 2)
    product_name = parts[1]
    total_rub = int(parts[2])
    
    expires = time.time() + 1800
    reservations[user_id] = {"product": product_name, "expires": expires, "total_rub": total_rub}
    
    btc_amt = total_rub / rates["btc"] if rates["btc"] > 0 else 0
    usdt_amt = total_rub / rates["usdt"] if rates["usdt"] > 0 else total_rub / 92
    ton_amt = total_rub / rates["ton"] if rates["ton"] > 0 else 0
    
    text = (
        f"🔒 <b>Товар забронирован на 30 минут!</b>\n\n"
        f"Товар: {product_name}\n"
        f"Сумма: <b>{total_rub:,} ₽</b>\n\n"
        f"🔸 BTC: {btc_amt:.8f} → {BTC_WALLET}\n"
        f"🔸 USDT (TRC20): {usdt_amt:.2f} → {USDT_WALLET}\n"
        f"🔸 TON: {ton_amt:.3f} → {TON_WALLET}\n\n"
        f"⏳ У тебя есть 30 минут на оплату."
    )
    await callback.message.edit_text(text)
    await callback.answer("✅ Забронировано!")
    
    asyncio.create_task(timer_warnings(user_id, expires))

async def timer_warnings(user_id: int, expires: float):
    await asyncio.sleep(1200)
    if user_id in reservations and reservations[user_id]["expires"] == expires:
        try:
            await bot.send_message(user_id, "⏰ Осталось 10 минут на оплату!")
        except:
            pass
    await asyncio.sleep(600)
    if user_id in reservations and reservations[user_id]["expires"] == expires:
        product = reservations[user_id]["product"]
        del reservations[user_id]
        try:
            await bot.send_message(user_id, f"⏰ Бронь на товар «{product}» снята.")
        except:
            pass

@dp.message(Command("paid"))
async def cmd_paid(message: types.Message):
    user_id = message.from_user.id
    res = reservations.get(user_id)
    if not res:
        return await message.answer("Нет активной брони.")
    if time.time() > res["expires"]:
        del reservations[user_id]
        return await message.answer("⏰ Бронь истекла.")
    
    await message.answer("🔍 Проверяю оплату...")
    await asyncio.sleep(1.5)
    await message.answer("⏳ Оплата ещё не пришла. Напиши /paid через 5 минут.")

async def main():
    asyncio.create_task(update_rates())
    print("🤖 Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())