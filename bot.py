import asyncio
import logging
import json
import os
import random
import time
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
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
FILE_ORDERS = "orders.json"

DEFAULT_CITIES = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань",
    "Нижний Новгород", "Челябинск", "Омск", "Самара", "Ростов-на-Дону",
    "Уфа", "Красноярск", "Воронеж", "Пермь", "Волгоград"
]

ALL_CITIES = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань", "Нижний Новгород", "Челябинск", "Омск", "Самара", "Ростов-на-Дону",
    "Уфа", "Красноярск", "Воронеж", "Пермь", "Волгоград", "Краснодар", "Саратов", "Тюмень", "Тольятти", "Ижевск", "Барнаул", "Ульяновск",
    "Иркутск", "Хабаровск", "Ярославль", "Владивосток", "Махачкала", "Томск", "Оренбург", "Кемерово", "Новокузнецк", "Рязань", "Астрахань",
    "Набережные Челны", "Пенза", "Липецк", "Тула", "Киров", "Чебоксары", "Курск", "Магнитогорск", "Сочи", "Калининград", "Брянск", "Иваново",
    "Белгород", "Ставрополь", "Симферополь", "Севастополь", "Курган", "Архангельск", "Сургут", "Владимир", "Чита", "Смоленск", "Калуга",
    "Кострома", "Грозный", "Якутск", "Сыктывкар", "Мурманск", "Тамбов", "Химки", "Балашиха", "Подольск", "Королёв", "Мытищи", "Люберцы",
    "Энгельс", "Великий Новгород", "Псков", "Саранск", "Йошкар-Ола", "Кызыл", "Абакан", "Петрозаводск", "Северодвинск", "Норильск",
    "Ангарск", "Благовещенск", "Братск", "Великие Луки", "Волжский", "Гатчина", "Дзержинск", "Димитровград", "Евпатория", "Жигулёвск",
    "Златоуст", "Ивантеевка", "Ишим", "Ишимбай", "Каменск-Уральский", "Камышин", "Керчь", "Кисловодск", "Ковров", "Коломна",
    "Комсомольск-на-Амуре", "Кропоткин", "Кстово", "Кузнецк", "Кыштым", "Ленинск-Кузнецкий", "Магадан", "Междуреченск", "Мичуринск", "Муром",
    "Находка", "Нефтекамск", "Нефтеюганск", "Нижневартовск", "Нижнекамск", "Новороссийск", "Новотроицк", "Новочебоксарск", "Новошахтинск", "Ногинск",
    "Обнинск", "Озёрск", "Октябрьский", "Орёл", "Орск", "Павлово", "Петропавловск-Камчатский", "Прокопьевск", "Пятигорск", "Рубцовск",
    "Рыбинск", "Салават", "Северск", "Серпухов", "Сызрань", "Сыктывкар", "Таганрог", "Тамбов", "Тверь", "Тобольск", "Торжок", "Туапсе",
    "Уссурийск", "Ухта", "Феодосия", "Ханты-Мансийск", "Череповец", "Черкесск", "Шахты", "Щёлково", "Элиста", "Южно-Сахалинск",
    "Азов", "Алапаевск", "Алексин", "Альметьевск", "Анапа", "Апатиты", "Арзамас", "Армавир", "Артём", "Асбест", "Ачинск", "Балаково",
    "Балахна", "Балашов", "Белово", "Белорецк", "Белореченск", "Бердск", "Березники", "Бийск", "Бор", "Борисоглебск", "Боровичи",
    "Будённовск", "Бузулук", "Великий Устюг", "Верхняя Пышма", "Видное", "Вихоревка", "Вольск", "Воткинск", "Выборг", "Выкса", "Вязьма",
    "Глазов", "Губкин", "Гуково", "Дербент", "Дмитров", "Донецк", "Донской", "Дубна", "Егорьевск", "Ейск", "Елец", "Ессентуки",
    "Железногорск", "Жуковский", "Зеленоград", "Зерноград", "Златоуст", "Ивантеевка", "Ишим", "Каменск-Шахтинский", "Камышлов", "Канск",
    "Каспийск", "Кинешма", "Кирсанов", "Клин", "Клинцы", "Ковров", "Колпино", "Копейск", "Котельники", "Котлас", "Краснотурьинск",
    "Красный Сулин", "Кропоткин", "Крымск", "Кстово", "Кузнецк", "Кунгур", "Лабинск", "Лесосибирск", "Лобня", "Лыткарино", "Майкоп",
    "Междуреченск", "Минеральные Воды", "Михайловка", "Михайловск", "Можайск", "Мончегорск", "Муром", "Мытищи", "Назрань", "Нальчик",
    "Находка", "Нерюнгри", "Нефтегорск", "Нефтекамск", "Нефтеюганск", "Нижневартовск", "Нижнекамск", "Новодвинск", "Новозыбков", "Новомосковск",
    "Новопавловск", "Новотроицк", "Новочебоксарск", "Новошахтинск", "Новочеркасск", "Ногинск", "Ноябрьск", "Нытва", "Обнинск", "Одинцово",
    "Озёрск", "Октябрьский", "Олекминск", "Оленегорск", "Онега", "Орёл", "Орск", "Павловский Посад", "Партизанск", "Петушки", "Печора",
    "Плесецк", "Покров", "Полярные Зори", "Приозерск", "Прокопьевск", "Прохладный", "Пушкин", "Пушкино", "Пятигорск", "Раменское",
    "Ревда", "Реутов", "Ржев", "Родники", "Россошь", "Рубцовск", "Руза", "Рыбинск", "Ряжск", "Салават", "Салехард", "Сафоново",
    "Свободный", "Северобайкальск", "Северо-Задонск", "Северодвинск", "Североморск", "Сегежа", "Сергиев Посад", "Сердобск", "Серпухов",
    "Сертолово", "Сестрорецк", "Сибай", "Славгород", "Славянск-на-Кубани", "Соликамск", "Солнечногорск", "Сосновый Бор", "Спасск-Дальний",
    "Старица", "Старый Оскол", "Стерлитамак", "Ступино", "Сургут", "Сызрань", "Сыктывкар", "Таганрог", "Тайга", "Тайшет", "Тамбов",
    "Тара", "Татарск", "Тверь", "Тейково", "Тихвин", "Тихорецк", "Тобольск", "Торжок", "Троицк", "Туапсе", "Туймазы", "Тула", "Туринск",
    "Тутаев", "Тында", "Тюмень", "Углич", "Удачный", "Улан-Удэ", "Ульяновск", "Усинск", "Усолье-Сибирское", "Уссурийск", "Усть-Илимск",
    "Усть-Каменогорск", "Усть-Лабинск", "Уфа", "Ухта", "Фрязино", "Фурманов", "Хабаровск", "Ханты-Мансийск", "Хасавюрт", "Химки",
    "Хотьково", "Чайковский", "Чапаевск", "Чебоксары", "Челябинск", "Черемхово", "Череповец", "Черкесск", "Черногорск", "Чистополь",
    "Чита", "Чкаловск", "Шадринск", "Шали", "Шахты", "Шебекино", "Шелехов", "Шуя", "Щёлково", "Электросталь", "Элиста", "Энгельс",
    "Южно-Сахалинск", "Юрга", "Якутск", "Ялта", "Ярославль", "Ясногорск"
]

LOCATIONS = {
    "Москва": ["Тверской", "Арбат", "Хамовники", "Якиманка", "Пресненский", "Любой район"],
    "Санкт-Петербург": ["Центральный", "Адмиралтейский", "Василеостровский", "Петроградский", "Выборгский", "Любой район"],
    "Екатеринбург": ["Верх-Исетский", "Октябрьский", "Железнодорожный", "Чкаловский", "Любой район"],
    "Новосибирск": ["Центральный", "Октябрьский", "Ленинский", "Советский", "Любой район"],
    "Краснодар": ["Центр", "Прикубанский", "Западный", "Любой район"],
    "Казань": ["Центр (Вахитовский)", "Советский", "Приволжский", "Любой район"],
}

MAIN_PRODUCTS = ["Футболка с принтом", "Худи oversize", "Кружка керамика", "Носки премиум", "Шапка зимняя"]
EXTRA_PRODUCTS = ["Бейсболка", "Рюкзак", "Сумка-тоут", "Термос", "Плед", "Флисовая кофта", "Джинсы", "Кроссовки", "Перчатки", "Шарф"]

# =====================================================

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)
rates = {"btc": 0.0, "usdt": 0.0, "ton": 0.0}

reservations = {}
orders = {}

def load_orders():
    if os.path.exists(FILE_ORDERS):
        with open(FILE_ORDERS, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

orders = load_orders()

def save_orders():
    with open(FILE_ORDERS, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

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
        [InlineKeyboardButton(text="🏙 Выбрать город", callback_data="start_city")],
        [InlineKeyboardButton(text="💰 Проверка оплаты", callback_data="check_payment")],
        [InlineKeyboardButton(text="📦 Ваш заказ", callback_data="my_order")],
        [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about_bot")]
    ])
    await message.answer("👋 Добро пожаловать в магазин!", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "my_order")
async def my_order(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🔍 Введите номер вашего заказа (7 цифр без пробелов):")
    await state.set_state(OrderStates.waiting_order_number)
    await callback.answer()

@dp.message(OrderStates.waiting_order_number)
async def check_order_number(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or len(text) != 7:
        await message.answer("❌ Номер заказа должен состоять из **ровно 7 цифр** без пробелов.")
        return
    order_id = text
    if order_id in orders:
        order = orders[order_id]
        await message.answer(f"✅ Заказ №{order_id} найден!\nТовар: {order['product']}\nСтатус: Оплачен")
    else:
        await message.answer("❌ Заказ не найден или оплата ещё не поступила.")
    await state.clear()

@dp.callback_query(lambda c: c.data == "start_city")
async def start_city_selection(callback: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=city, callback_data=f"city_{city}")] for city in DEFAULT_CITIES
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🌍 Другой город", callback_data="city_other")])
    await callback.message.edit_text("Выбери город доставки:", reply_markup=keyboard)
    await state.set_state(OrderStates.waiting_city)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("city_") and c.data != "city_other")
async def choose_product(callback: types.CallbackQuery, state: FSMContext):
    city = callback.data.replace("city_", "")
    await state.update_data(city=city)
    
    city_index = DEFAULT_CITIES.index(city) if city in DEFAULT_CITIES else 999
    if city_index < 100:
        products_to_show = MAIN_PRODUCTS.copy()
        num_extra = random.randint(2, 6)
    else:
        products_to_show = []
        num_extra = random.randint(1, 4)
    
    extra = random.sample(EXTRA_PRODUCTS, num_extra)
    products_to_show.extend(extra)
    random.shuffle(products_to_show)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"product_{name}")] for name in products_to_show
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="← Назад", callback_data="back_to_city")])
    
    await callback.message.edit_text(f"📍 Город: <b>{city}</b>\nВыбери товар:", reply_markup=keyboard)
    await state.set_state(OrderStates.waiting_product)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_city")
async def back_to_city(callback: types.CallbackQuery, state: FSMContext):
    await start_city_selection(callback, state)

@dp.callback_query(lambda c: c.data == "city_other")
async def ask_custom_city(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🌍 Напиши любой город:")
    await state.set_state(OrderStates.waiting_city)

@dp.message(OrderStates.waiting_city)
async def handle_custom_city(message: types.Message, state: FSMContext):
    city = message.text.strip()
    
    if city.lower() not in [c.lower() for c in ALL_CITIES]:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="← Назад к списку", callback_data="back_to_city")]
        ])
        await message.answer(f"❌ Города **{city}** нет в базе.", reply_markup=keyboard)
        await state.set_state(OrderStates.waiting_city)
        return
    
    await state.update_data(city=city)
    products_to_show = MAIN_PRODUCTS.copy() if DEFAULT_CITIES.index(city) < 100 else []
    num_extra = random.randint(2, 6) if DEFAULT_CITIES.index(city) < 100 else random.randint(1, 4)
    extra = random.sample(EXTRA_PRODUCTS, num_extra)
    products_to_show.extend(extra)
    random.shuffle(products_to_show)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"product_{name}")] for name in products_to_show
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="← Назад", callback_data="back_to_city")])
    
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
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="← Назад", callback_data="back_to_product")])
    
    await callback.message.edit_text(
        f"🎁 <b>{product_name}</b> — {price:,} ₽\n"
        f"📦 В наличии: <b>{stock}</b>\n"
        f"📍 {city}\nВыбери район:",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_product")
async def back_to_product(callback: types.CallbackQuery, state: FSMContext):
    await choose_product(callback, state)

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
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="← Назад", callback_data="back_to_district")])
    
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

@dp.callback_query(lambda c: c.data == "back_to_district")
async def back_to_district(callback: types.CallbackQuery, state: FSMContext):
    await choose_district(callback, state)

@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def process_payment(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    parts = callback.data.split("_", 2)
    product_name = parts[1]
    total_rub = int(parts[2])
    
    order_id = str(random.randint(1000000, 9999999))
    
    expires = time.time() + 1800
    reservations[user_id] = {"product": product_name, "expires": expires, "total_rub": total_rub, "order_id": order_id}
    
    orders[order_id] = {"product": product_name, "amount": total_rub, "status": "pending"}
    save_orders()
    
    btc_amt = total_rub / rates["btc"] if rates["btc"] > 0 else 0
    usdt_amt = total_rub / rates["usdt"] if rates["usdt"] > 0 else total_rub / 92
    ton_amt = total_rub / rates["ton"] if rates["ton"] > 0 else 0
    
    text = (
        f"🔒 <b>Товар забронирован на 30 минут!</b>\n\n"
        f"Номер заказа: <b>{order_id}</b>\n"
        f"Товар: {product_name}\n"
        f"Сумма: <b>{total_rub:,} ₽</b>\n\n"
        f"🔸 BTC: {btc_amt:.8f} → {BTC_WALLET}\n"
        f"🔸 USDT (TRC20): {usdt_amt:.2f} → {USDT_WALLET}\n"
        f"🔸 TON: {ton_amt:.3f} → {TON_WALLET}\n\n"
        f"⚠️ Кошельки и сумма действуют **только до истечения брони**.\n"
        f"⏳ У тебя есть 30 минут на оплату.\n"
        f"После перевода **обязательно** напиши /paid"
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