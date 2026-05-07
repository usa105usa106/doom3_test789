import asyncio
import logging
import os
import random
import time
import json
import urllib.request
import re
from html import escape

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
# ADMIN CONFIG
# =====================
# Можно указать админов двумя способами:
# 1) через переменную окружения ADMIN_IDS=123456789,987654321
# 2) прямо в коде: HARD_ADMIN_IDS = [123456789]
# Бот также понимает ADMIN_ID, admin_ids и даже amdin_ids, если переменная была названа с опечаткой.

HARD_ADMIN_IDS: list[int] = []

def _load_admin_ids() -> set[int]:
    """
    Надёжно читает ID админов из переменных окружения и из HARD_ADMIN_IDS.

    Поддерживает варианты:
    ADMIN_IDS=123456789
    ADMIN_IDS=123456789,987654321
    ADMIN_IDS=[123456789, 987654321]
    ADMIN_ID=123456789
    admin_ids=123456789
    amdin_ids=123456789  # частая опечатка
    """
    raw_values = [
        os.getenv("ADMIN_IDS", ""),
        os.getenv("ADMIN_ID", ""),
        os.getenv("admin_ids", ""),
        os.getenv("admin_id", ""),
        os.getenv("amdin_ids", ""),
        os.getenv("AMDIN_IDS", ""),
        os.getenv("ADMINS", ""),
        os.getenv("BOT_ADMIN_IDS", ""),
        os.getenv("BOT_ADMIN_ID", ""),
    ]

    ids: set[int] = set()
    for item in HARD_ADMIN_IDS:
        try:
            ids.add(int(item))
        except (TypeError, ValueError):
            pass

    for raw in raw_values:
        # regex достаёт цифры даже из строк вида [123, 456] или "123"
        for part in re.findall(r"\d+", str(raw)):
            try:
                ids.add(int(part))
            except ValueError:
                pass

    logging.info("Loaded admin IDs: %s", sorted(ids) if ids else "NONE")
    return ids

ADMIN_IDS = _load_admin_ids()
AUTO_ADMIN_FILE = "admin_ids.json"

def _save_admin_ids() -> None:
    try:
        with open(AUTO_ADMIN_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(ADMIN_IDS), f, ensure_ascii=False)
    except Exception as e:
        logging.warning("Could not save admin IDs: %s", e)

def _load_auto_admin_ids() -> None:
    try:
        if os.path.exists(AUTO_ADMIN_FILE):
            with open(AUTO_ADMIN_FILE, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    ADMIN_IDS.add(int(item))
    except Exception as e:
        logging.warning("Could not load admin IDs file: %s", e)

_load_auto_admin_ids()

def is_admin(user_id: int | None) -> bool:
    if user_id is None:
        return False
    # ADMIN_IDS загружается при старте контейнера, поэтому после изменения переменных нужен redeploy/restart.
    return int(user_id) in ADMIN_IDS

async def admin_only(m: types.Message) -> bool:
    user_id = m.from_user.id if m.from_user else None
    if is_admin(user_id):
        return True

    await m.answer(
        "⛔ Эта команда доступна только администратору бота.\n"
        f"Ваш Telegram ID: <code>{user_id}</code>\n\n"
        "Проверьте переменную окружения <code>ADMIN_IDS</code>.\n"
        "Пример: <code>ADMIN_IDS=123456789</code>\n"
        "После изменения переменной обязательно перезапустите deploy/container."
    )
    return False

# =====================
# STATES
# =====================

class S(StatesGroup):
    city = State()
    product = State()
    district = State()
    city_name = State()
    cash_wallet = State()

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

# Дополнительные товары.
# Для каждого города к 5 основным товарам добавляется случайный набор
# от 3 до 6 товаров. Набор стабилен для одного и того же города.
EXTRA_PRODUCTS = {
    "Рюкзак": 2200,
    "Кепка": 700,
    "Носки": 350,
    "Куртка": 5200,
    "Джинсы": 2800,
    "Перчатки": 650,
    "Очки": 1100,
    "Пояс": 800,
    "Сумка": 1900,
    "Кошелёк": 1200,
    "Поло": 1500,
    "Брюки": 2400,
}

def city_products(city: str) -> dict:
    """5 основных товаров + 3-6 дополнительных для выбранного города."""
    result = dict(PRODUCTS)
    if EXTRA_PRODUCTS:
        rnd = random.Random(city)
        count = min(rnd.randint(3, 6), len(EXTRA_PRODUCTS))
        extra_names = rnd.sample(list(EXTRA_PRODUCTS.keys()), count)
        for name in extra_names:
            result[name] = EXTRA_PRODUCTS[name]
    return result

def city_keyboard():
    # В меню показываются только 15 самых крупных городов.
    # Остальные города вводятся вручную через кнопку «Другой город».
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=x, callback_data=f"c_{x}")] for x in ALL_CITIES[:15]
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔎 Другой город", callback_data="other_city")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])
    return kb

def products_keyboard(city: str):
    products = city_products(city)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{p} — {price} ₽", callback_data=f"p_{p}")]
        for p, price in products.items()
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="🔙 Города", callback_data="city"),
        InlineKeyboardButton(text="🏠 Меню", callback_data="menu")
    ])
    return kb


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

TOP_CITIES = set(ALL_CITIES[:50])
FALLBACK_DISTRICTS = ["Автовокзал", "ЖД/вокзал", "Любой район"]
GENERIC_TOP_DISTRICTS = ["Центр", "Ленинский", "Советский", "Октябрьский", "Центральный"]

def get_city_districts(city: str) -> list[str]:
    """
    Для первых 50 крупных городов — до 5 районов.
    Для остальных городов — всегда Центр + случайно 1-3 варианта
    из Автовокзал / ЖД/вокзал / Любой район. Набор стабилен для города.
    """
    if city in TOP_CITIES:
        return (LOCATIONS.get(city) or GENERIC_TOP_DISTRICTS)[:5]

    rnd = random.Random(f"districts:{city}")
    count = rnd.randint(1, 3)
    random_districts = rnd.sample(FALLBACK_DISTRICTS, count)
    return ["Центр"] + random_districts

# WALLETS
WALLETS = {
    "btc": ["bc1qexample"],
    "usdt": ["TXexample"],
    "ton": ["UQexample"],
}
WALLET_TITLES = {
    "btc": "BTC",
    "usdt": "USDT-(TRC20)",
    "ton": "TON",
}


def get_random_wallet(wallet_type: str) -> str:
    wallets = WALLETS.get(wallet_type, [])
    if not wallets:
        return "не задан"
    return random.choice(wallets)

def wallets_text(wallet_type: str) -> str:
    wallets = WALLETS.get(wallet_type, [])
    if not wallets:
        return "не задан"
    return "\n".join(f"• <code>{escape(w)}</code>" for w in wallets)

def wallets_info_text() -> str:
    """Текущий список введённых кошельков."""
    lines = ["💳 <b>Введённые кошельки</b>", ""]
    for key in ("btc", "usdt", "ton"):
        wallet = WALLETS.get(key) or "не задан"
        lines.append(f"{WALLET_TITLES[key]}: <code>{escape(wallet)}</code>")
    return "\n".join(lines)

def products_info_text() -> str:
    """Весь введённый товар с ценами."""
    if not PRODUCTS and not EXTRA_PRODUCTS:
        return "📦 <b>Товары</b>\n\nСписок товаров пуст."

    lines = ["📦 <b>Введённый товар с ценами</b>", ""]
    used: set[str] = set()

    for name, price in sorted(PRODUCTS.items(), key=lambda x: x[0].lower()):
        used.add(name.lower())
        lines.append(f"• <b>{escape(name)}</b> — <code>{int(price)} ₽</code>")

    for name, price in sorted(EXTRA_PRODUCTS.items(), key=lambda x: x[0].lower()):
        if name.lower() in used:
            continue
        lines.append(f"• <b>{escape(name)}</b> — <code>{int(price)} ₽</code>")

    return "\n".join(lines)

# Резервные курсы на случай, если сервер не сможет получить актуальный курс из интернета.
# Сумма в криптовалюте считается строго так: цена_в_рублях / курс_криптовалюты_в_рублях.
BTC_RATE = float(os.getenv("BTC_RATE", "9500000"))
USDT_TRC20_RATE = float(os.getenv("USDT_TRC20_RATE", "90"))
TON_RATE = float(os.getenv("TON_RATE", "270"))
_rates_cache = {"ts": 0, "rates": None}

ABOUT_TEXT = "🛒 Это автоматический маркетплейс.\nОплата только в криптовалюте.\nКошельки действительны 30 минут."

def fmt_amount(value: float, decimals: int) -> str:
    """Формат без лишних нулей и без пробелов вокруг точки."""
    return f"{value:.{decimals}f}".rstrip("0").rstrip(".")

def get_live_rates() -> dict:
    """Получает актуальные курсы BTC/USDT/TON к RUB. При ошибке использует резервные курсы."""
    now = time.time()
    if _rates_cache["rates"] and now - _rates_cache["ts"] < 300:
        return _rates_cache["rates"]

    fallback = {"btc": BTC_RATE, "usdt": USDT_TRC20_RATE, "ton": TON_RATE}
    url = (
        "https://api.coingecko.com/api/v3/simple/price"
        "?ids=bitcoin,tether,the-open-network&vs_currencies=rub"
    )
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        rates = {
            "btc": float(data["bitcoin"]["rub"]),
            "usdt": float(data["tether"]["rub"]),
            "ton": float(data["the-open-network"]["rub"]),
        }
        _rates_cache.update({"ts": now, "rates": rates})
        return rates
    except Exception as e:
        logging.warning("Не удалось получить актуальные курсы, используются резервные: %s", e)
        return fallback

def get_crypto_amounts(rub: int):
    rates = get_live_rates()
    btc = fmt_amount(rub / rates["btc"], 8)
    usdt = fmt_amount(rub / rates["usdt"], 2)
    ton = fmt_amount(rub / rates["ton"], 3)
    return btc, usdt, ton

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

@dp.message(F.text.regexp(r"^/start(@\w+)?$"))
async def start(m: types.Message):
    # Если админ не задан ни в переменных, ни в файле, первый пользователь /start становится админом.
    # Это спасает от ошибок с ADMIN_IDS/amdin_ids.
    if not ADMIN_IDS and m.from_user:
        ADMIN_IDS.add(int(m.from_user.id))
        _save_admin_ids()
        logging.info("Auto admin created: %s", m.from_user.id)
        await m.answer(
            "✅ Админ не был задан, поэтому вы назначены администратором.\n"
            f"Ваш Telegram ID: <code>{m.from_user.id}</code>"
        )
    await m.answer("🏪 Добро пожаловать в Маркетплейс", reply_markup=main_kb())

# =====================
# MAIN MENU BUTTONS
# =====================

@dp.message(F.text == "🏙 Выбрать город")
async def choose_city_btn(m: types.Message, state: FSMContext):
    data = await state.get_data()
    # Не сбрасываем данные активной брони 30 минут: товар, город и районы сохраняются.
    if time.time() - data.get("t", 0) > 1800:
        await state.clear()
    await m.answer("🏙 Выберите город:", reply_markup=city_keyboard())

@dp.message(F.text == "📦 Мой заказ")
async def my_order(m: types.Message):
    await m.answer("📦 У вас ещё нет покупок, сначала произведите оплату.")

@dp.message(F.text == "💰 Проверить оплату")
async def check_payment_btn(m: types.Message):
    await m.answer("💰 Отправьте боту в чат номер вашего заказа (только цифры). Внимание!!! Через 24 часа после покупки проверка заказа будет недоступна.")

@dp.message(F.text == "ℹ️ О боте")
async def about(m: types.Message):
    await m.answer(ABOUT_TEXT)

def command_args(text: str) -> str:
    """Возвращает текст после команды, поддерживает /cmd и /cmd@BotName."""
    parts = (text or "").split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""

@dp.message(F.text.regexp(r"^/help(@\w+)?$"))
async def help_cmd(m: types.Message):
    if not await admin_only(m):
        return
    await m.answer(
        "📋 <b>Список команд</b>\n\n"
        "/start — открыть главное меню\n"
        "/help — список команд администратора\n"
        "/add товар цена — добавить товар, пример: <code>/add книга 500</code>\n"
        "/add info — показать весь введённый товар с ценами\n"
        "/del товар — удалить товар, пример: <code>/del книга</code>\n"
        "/del all — удалить весь товар\n"
        "/info текст — изменить сообщение кнопки «О боте»\n"
        "/cash info — список введённых кошельков\n"
        "/cash btc — задать BTC кошелёк\n"
        "/cash usdt — задать USDT-(TRC20) кошелёк\n"
        "/cash ton — задать TON кошелёк\n"
        "/cash del btc|usdt|ton — удалить выбранный кошелёк\n"
        "/cash del all — удалить все кошельки"
    )

@dp.message(F.text.regexp(r"^/add(@\w+)?(\s|$)"))
async def add_product_cmd(m: types.Message):
    if not await admin_only(m):
        return
    rest = command_args(m.text)

    if rest.lower() == "info":
        await m.answer(products_info_text())
        return

    if not rest or len(rest.split()) < 2:
        await m.answer("❌ Неверный формат. Пример: <code>/add книга 500</code>\nПосмотреть товары: <code>/add info</code>")
        return

    name, price_text = rest.rsplit(maxsplit=1)
    if not price_text.isdigit() or int(price_text) <= 0:
        await m.answer("❌ Цена должна быть положительным числом. Пример: <code>/add книга 500</code>")
        return

    PRODUCTS[name.strip().capitalize()] = int(price_text)
    await m.answer(f"✅ Товар добавлен: <b>{escape(name.strip().capitalize())}</b> — <b>{int(price_text)} ₽</b>")

@dp.message(F.text.regexp(r"^/del(@\w+)?\s+"))
async def del_product_cmd(m: types.Message):
    if not await admin_only(m):
        return
    name = command_args(m.text)
    if not name:
        await m.answer("❌ Неверный формат. Пример: <code>/del книга</code>")
        return

    if name.lower() == "all":
        PRODUCTS.clear()
        EXTRA_PRODUCTS.clear()
        await m.answer("✅ Весь товар удалён.")
        return

    key = next((x for x in list(PRODUCTS.keys()) if x.lower() == name.lower()), None)
    extra_key = next((x for x in list(EXTRA_PRODUCTS.keys()) if x.lower() == name.lower()), None)

    deleted = False
    if key:
        PRODUCTS.pop(key, None)
        deleted = True
    if extra_key:
        EXTRA_PRODUCTS.pop(extra_key, None)
        deleted = True

    if deleted:
        await m.answer(f"✅ Товар удалён: <b>{escape(name)}</b>")
    else:
        await m.answer("❌ Такой товар не найден.")

@dp.message(F.text.regexp(r"^/info(@\w+)?\s+"))
async def info_cmd(m: types.Message):
    if not await admin_only(m):
        return
    global ABOUT_TEXT
    text = command_args(m.text)
    if not text:
        await m.answer("❌ Напишите текст после команды. Пример: <code>/info Новый текст</code>")
        return
    ABOUT_TEXT = text
    await m.answer("✅ Сообщение кнопки «О боте» изменено.")


@dp.message(F.text.regexp(r"^/cash(@\w+)?(\s|$)"))
async def cash_cmd(m: types.Message, state: FSMContext):
    if not await admin_only(m):
        return

    args = command_args(m.text)
    parts = args.split(maxsplit=2)
    if not parts:
        await m.answer(
            wallets_info_text() +
            "\n\nКоманды:\n"
            "<code>/cash info</code> — список введённых кошельков\n"
            "<code>/cash btc</code> — задать BTC кошелёк\n"
            "<code>/cash usdt</code> — задать USDT-(TRC20) кошелёк\n"
            "<code>/cash ton</code> — задать TON кошелёк\n"
            "<code>/cash del btc</code> — удалить BTC кошелёк\n"
            "<code>/cash del all</code> — удалить все кошельки"
        )
        return

    action = parts[0].lower()

    if action == "info":
        await m.answer(wallets_info_text())
        return

    if action == "del":
        if len(parts) < 2:
            await m.answer("❌ Укажите, какой кошелёк удалить: <code>/cash del btc</code>, <code>/cash del usdt</code>, <code>/cash del ton</code> или <code>/cash del all</code>")
            return
        target = parts[1].lower()
        if target == "all":
            for key in WALLETS:
                WALLETS[key] = []
            await m.answer("✅ Все кошельки удалены.")
            return
        if target not in WALLETS:
            await m.answer("❌ Можно удалить только: btc, usdt, ton или all.")
            return
        WALLETS[target] = []
        await m.answer(f"✅ Кошелёк {WALLET_TITLES[target]} удалён.")
        return

    if action not in WALLETS:
        await m.answer("❌ Неверная команда. Используйте: <code>/cash btc</code>, <code>/cash usdt</code>, <code>/cash ton</code>, <code>/cash del ...</code>")
        return

    if len(parts) >= 2:
        wallet = parts[1].strip()
        if not wallet:
            await m.answer("❌ Кошелёк не может быть пустым.")
            return
        WALLETS[action].append(wallet)
        await state.clear()
        await m.answer(f"✅ Кошелёк {WALLET_TITLES[action]} сохранён: <code>{escape(wallet)}</code>")
        return

    await state.update_data(cash_type=action)
    await state.set_state(S.cash_wallet)
    await m.answer(f"✍️ Отправьте адрес кошелька {WALLET_TITLES[action]} в чат.")

@dp.message(S.cash_wallet)
async def cash_wallet_from_chat(m: types.Message, state: FSMContext):
    if not await admin_only(m):
        return
    data = await state.get_data()
    cash_type = data.get("cash_type")
    if cash_type not in WALLETS:
        await state.clear()
        await m.answer("❌ Тип кошелька не найден. Повторите команду /cash.")
        return
    wallet = m.text.strip()
    if not wallet:
        await m.answer("❌ Кошелёк не может быть пустым.")
        return
    WALLETS[cash_type].append(wallet)
    await state.clear()
    await m.answer(f"✅ Кошелёк {WALLET_TITLES[cash_type]} сохранён: <code>{escape(wallet)}</code>")

# =====================
# INLINE HANDLERS
# =====================

@dp.callback_query(F.data == "menu")
async def menu(c: types.CallbackQuery):
    await c.message.edit_text("🏪 Главное меню", reply_markup=None)
    await c.message.answer("Выберите действие:", reply_markup=main_kb())

@dp.callback_query(F.data == "city")
async def back_to_cities(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(S.city)
    await c.message.edit_text("🏙 Выберите город:", reply_markup=city_keyboard())

@dp.callback_query(F.data == "other_city")
async def other_city(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(S.city_name)
    await c.message.edit_text("✍️ Напишите название города в чат.")

@dp.message(F.text.regexp(r"^\d+$"))
async def order_number_from_chat(m: types.Message):
    digits = m.text.strip()
    if len(digits) == 7:
        await m.answer("⛔ По данному заказу оплата не была получена, сначала оплатите и повторите запрос.")
    elif 1 <= len(digits) <= 6 or 8 <= len(digits) <= 20:
        await m.answer("❌ Неверный ввод, убедитесь, что вы вводите 7 цифр вашего заказа.")

@dp.message(S.city_name)
async def city_name_from_chat(m: types.Message, state: FSMContext):
    city = m.text.strip()
    if not city:
        await m.answer("Напишите название города.")
        return

    # Если город есть в списке — берём написание из списка, иначе принимаем введённый город.
    matches = [x for x in ALL_CITIES if x.lower() == city.lower()]
    city = matches[0] if matches else city[:64]

    await state.update_data(city=city)
    await state.set_state(S.product)
    await m.answer(f"📍 Город: <b>{escape(city)}</b>\n\n🛍 Выберите товар:", reply_markup=products_keyboard(city))

# 1. ГОРОД
@dp.callback_query(F.data.startswith("c_"))
async def city_selected(c: types.CallbackQuery, state: FSMContext):
    city = c.data[2:]
    await state.update_data(city=city)
    await state.set_state(S.product)

    await c.message.edit_text(f"📍 Город: <b>{city}</b>\n\n🛍 Выберите товар:", reply_markup=products_keyboard(city))

# 2. ТОВАР
@dp.callback_query(F.data.startswith("p_"))
async def product_selected(c: types.CallbackQuery, state: FSMContext):
    product = c.data[2:]
    data = await state.get_data()
    city = data.get('city')
    if not city:
        await c.answer("Сначала выберите город", show_alert=True)
        return

    products = city_products(city)
    if product not in products:
        await c.answer("Товар недоступен для этого города", show_alert=True)
        return

    districts = get_city_districts(city)
    # Запоминаем выбранный товар и список районов до окончания брони.
    await state.update_data(product=product, price=products[product], districts=districts)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=d, callback_data=f"d_{d}")] for d in districts
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="🔙 Товары", callback_data=f"back_products"),
        InlineKeyboardButton(text="🏠 Меню", callback_data="menu")
    ])

    await c.message.edit_text(f"📍 {city}\n🛍 Товар: <b>{product}</b>\n\nВыберите район:", reply_markup=kb)

@dp.callback_query(F.data == "back_products")
async def back_products(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    city = data.get("city")
    if not city:
        await c.message.edit_text("🏙 Сначала выберите город:", reply_markup=city_keyboard())
        return
    await c.message.edit_text(f"📍 Город: <b>{city}</b>\n\n🛍 Выберите товар:", reply_markup=products_keyboard(city))

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
    # Берём актуальные кошельки из WALLETS в момент создания оплаты.
    # Это гарантирует, что в оплате показывается последний введённый админом адрес,
    # а не случайное/старое значение из состояния пользователя.
    payment_wallets = {key: WALLETS.get(key) or "не задан" for key in ("btc", "usdt", "ton")}

    text = (
        f"🆔 <b>Заказ №{order_id}</b>\n\n"
        f"Товар: <b>{product}</b>\n"
        f"Город: <b>{city}</b>\n"
        f"Район: <b>{district}</b>\n\n"
        f"Сумма: <b>{price} ₽</b>\n\n"
        f"🔹 BTC: <code>{btc}</code> → {escape(payment_wallets['btc'])}\n"
        f"🔹 USDT-(TRC20): <code>{usdt}</code> → {escape(payment_wallets['usdt'])}\n"
        f"🔹 TON: <code>{ton}</code> → {escape(payment_wallets['ton'])}\n\n"
        f"⏰ Внимание!!! Для покупки товара, оплатите точную сумму на любой из этих кошельков. Бот находит оплату автоматически после первого подтверждения транзакции в сети. В целях идентификации платежа - кошельки и сумма актуальны 30 минут. Если у вас нет криптовалюты, её можно купить за рубли через обменник bestchange.biz , для создания кошельков используйте trust wallet, скачать можно через google play/app store."
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
            f"⏳ Заказ №{order_id}\n\nВаша бронь действительна ещё 10 минут."
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
    await c.answer("⛔ По данному заказу оплата не была получена, сначала оплатите и повторите запрос.", show_alert=True)


@dp.message(F.text.startswith("/"))
async def unknown_or_forbidden_command(m: types.Message):
    if not is_admin(m.from_user.id if m.from_user else None):
        await m.answer("⛔ Эта команда доступна только администратору бота.")
    else:
        await m.answer("❌ Неизвестная команда. Используйте /help")

# =====================
# RUN
# =====================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())