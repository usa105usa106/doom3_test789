import asyncio
import json
import logging
import os
import random
import re
import sqlite3
import time
import urllib.request
from html import escape
from pathlib import Path

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set")

DB_PATH = os.getenv("DB_PATH", "/data/bot.db" if os.path.exists("/data") else "bot.db")
ADMIN_FILE = "admin_ids.json"
HARD_ADMIN_IDS = [5172121123]

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

BTC_RATE = float(os.getenv("BTC_RATE", "9500000"))
USDT_RATE = float(os.getenv("USDT_RATE", os.getenv("USDT_TRC20_RATE", "90")))
TON_RATE = float(os.getenv("TON_RATE", "270"))
USE_LIVE_RATES = os.getenv("USE_LIVE_RATES", "1").strip() != "0"
_rates_cache = {"ts": 0.0, "rates": None}

ALL_CITIES = [
"Москва","Санкт-Петербург","Новосибирск","Екатеринбург","Казань","Нижний Новгород","Челябинск","Омск","Самара","Ростов-на-Дону",
"Уфа","Красноярск","Воронеж","Пермь","Волгоград","Краснодар","Саратов","Тюмень","Тольятти","Ижевск","Барнаул","Ульяновск","Иркутск",
"Хабаровск","Ярославль","Владивосток","Махачкала","Томск","Оренбург","Кемерово","Новокузнецк","Рязань","Астрахань","Пенза","Липецк",
"Киров","Чебоксары","Брянск","Тула","Курск","Ставрополь","Улан-Удэ","Тверь","Магнитогорск","Сочи","Иваново","Белгород","Архангельск",
"Калининград","Владимир","Смоленск","Калуга","Чита","Грозный","Якутск","Сургут","Нижневартовск","Набережные Челны","Стерлитамак","Орёл",
"Волжский","Кострома","Петрозаводск","Новороссийск","Йошкар-Ола","Сыктывкар","Нальчик","Абакан","Благовещенск","Дзержинск","Шахты",
"Энгельс","Балаково","Прокопьевск","Армавир","Псков","Бийск","Рубцовск","Норильск","Северодвинск","Ангарск","Братск","Южно-Сахалинск",
"Каменск-Уральский","Орск","Златоуст","Элиста","Петропавловск-Камчатский","Нижнекамск","Химки","Королёв","Мытищи","Подольск","Люберцы",
"Серпухов","Одинцово","Красногорск","Балашиха","Раменское","Жуковский","Мурманск","Вологда","Череповец","Владикавказ","Саранск",
"Тамбов","Таганрог","Комсомольск-на-Амуре","Старый Оскол","Великий Новгород","Нижний Тагил","Димитровград","Назрань","Хасавюрт",
"Каспийск","Дербент","Кызыл","Миасс","Находка","Уссурийск","Коломна","Электросталь","Домодедово","Щёлково","Новомосковск","Первоуральск",
"Березники","Кисловодск","Ессентуки","Пятигорск","Невинномысск","Ковров","Муром","Новочеркасск","Батайск","Каменск-Шахтинский","Азов",
"Елец","Мичуринск","Обнинск","Северск","Ачинск","Канск","Минусинск","Лесосибирск","Нефтеюганск","Ноябрьск","Новый Уренгой","Муравленко",
"Губкинский","Салехард","Лабытнанги","Ханты-Мансийск","Когалым","Мегион","Радужный","Лангепас","Пыть-Ях","Ишим","Тобольск","Нефтекамск",
"Октябрьский","Салават","Ишимбай","Белорецк","Сибай","Кумертау","Мелеуз","Бирск","Туймазы","Бугульма","Альметьевск","Елабуга",
"Зеленодольск","Бавлы","Лениногорск","Чистополь","Нурлат","Азнакаево","Глазов","Воткинск","Сарапул","Можга","Чайковский","Соликамск",
"Кунгур","Лысьва","Краснокамск","Губаха","Добрянка","Кудымкар","Серов","Асбест","Полевской","Ревда","Верхняя Пышма","Новоуральск",
"Краснотурьинск","Лесной","Качканар","Алапаевск","Ирбит","Копейск","Троицк","Озёрск","Снежинск","Сатка","Аша","Коркино",
"Южноуральск","Еманжелинск","Кыштым","Курган","Шадринск","Далматово","Петухово","Макушино","Бугуруслан","Бузулук","Гай","Новотроицк",
"Соль-Илецк","Медногорск","Сорочинск","Кувандык","Сызрань","Новокуйбышевск","Чапаевск","Отрадный","Жигулёвск","Кинель","Похвистнево"
]
ALL_CITIES = list(dict.fromkeys(ALL_CITIES))
CITY_CODES = {city: str(i) for i, city in enumerate(ALL_CITIES)}
CODE_CITIES = {str(i): city for i, city in enumerate(ALL_CITIES)}
TOP_CITIES = set(ALL_CITIES[:50])

LOCATIONS = {
    "Москва": ["Тверской", "Арбат", "Хамовники", "Пресненский", "Басманный"],
    "Санкт-Петербург": ["Центральный", "Адмиралтейский", "Петроградский", "Выборгский", "Василеостровский"],
    "Новосибирск": ["Центральный", "Ленинский", "Октябрьский", "Советский", "Калининский"],
    "Екатеринбург": ["Ленинский", "Кировский", "Чкаловский", "Железнодорожный", "Октябрьский"],
    "Казань": ["Вахитовский", "Советский", "Московский", "Кировский", "Приволжский"],
    "Нижний Новгород": ["Нижегородский", "Советский", "Автозаводский", "Сормовский", "Канавинский"],
    "Челябинск": ["Центральный", "Калининский", "Курчатовский", "Советский", "Металлургический"],
    "Омск": ["Центральный", "Советский", "Кировский", "Ленинский", "Октябрьский"],
    "Самара": ["Ленинский", "Октябрьский", "Промышленный", "Советский", "Куйбышевский"],
    "Ростов-на-Дону": ["Ленинский", "Кировский", "Ворошиловский", "Советский", "Октябрьский"],
    "Уфа": ["Советский", "Кировский", "Октябрьский", "Ленинский", "Калининский"],
    "Красноярск": ["Центральный", "Советский", "Свердловский", "Железнодорожный", "Кировский"],
    "Воронеж": ["Центральный", "Коминтерновский", "Советский", "Левобережный", "Железнодорожный"],
    "Пермь": ["Ленинский", "Свердловский", "Индустриальный", "Мотовилихинский", "Орджоникидзевский"],
    "Волгоград": ["Центральный", "Дзержинский", "Краснооктябрьский", "Ворошиловский", "Тракторозаводский"],
}
FALLBACK_DISTRICTS = ["Центр", "Автовокзал", "ЖД/вокзал", "Любой район", "Ленинский", "Советский", "Октябрьский", "Центральный"]
GENERIC_TOP_DISTRICTS = ["Центр", "Ленинский", "Советский", "Октябрьский", "Центральный"]

class S(StatesGroup):
    city_name = State()
    cash_wallet = State()
    support_message = State()

def db():
    parent = os.path.dirname(DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")
    return con

def init_db():
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS products(
                name TEXT PRIMARY KEY,
                price INTEGER NOT NULL,
                group_name TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS wallets(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                address TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS processed(
                key TEXT PRIMARY KEY,
                created_at REAL NOT NULL
            )
        """)
        con.commit()

init_db()

def processed_once(key: str) -> bool:
    """True = можно обрабатывать. False = дубль."""
    now = time.time()
    try:
        with db() as con:
            con.execute("DELETE FROM processed WHERE created_at < ?", (now - 120,))
            con.execute("INSERT INTO processed(key, created_at) VALUES(?, ?)", (key, now))
            con.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception:
        return True

@dp.message.outer_middleware()
async def dedupe_messages(handler, event: types.Message, data: dict):
    key = f"m:{event.chat.id}:{event.message_id}"
    if not processed_once(key):
        return
    return await handler(event, data)

@dp.callback_query.outer_middleware()
async def dedupe_callbacks(handler, event: types.CallbackQuery, data: dict):
    # отвечаем сразу, чтобы кнопка не пульсировала
    try:
        await event.answer()
    except Exception:
        pass
    key = f"c:{event.id}"
    if not processed_once(key):
        return
    return await handler(event, data)

def load_admin_ids() -> set[int]:
    ids = {int(x) for x in HARD_ADMIN_IDS}
    for name in ["ADMIN_IDS", "ADMIN_ID", "admin_ids", "admin_id", "ADMINS"]:
        for part in re.findall(r"\d+", os.getenv(name, "")):
            ids.add(int(part))
    try:
        if os.path.exists(ADMIN_FILE):
            with open(ADMIN_FILE, "r", encoding="utf-8") as f:
                for x in json.load(f):
                    ids.add(int(x))
    except Exception:
        pass
    return ids

ADMIN_IDS = load_admin_ids()

def save_admin_ids():
    try:
        with open(ADMIN_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(ADMIN_IDS), f, ensure_ascii=False)
    except Exception:
        pass

def is_admin(user_id: int | None) -> bool:
    return user_id is not None and int(user_id) in ADMIN_IDS

async def admin_only(m: types.Message) -> bool:
    uid = m.from_user.id if m.from_user else None
    if is_admin(uid):
        return True
    await m.answer(f"⛔ Только администратор.\nВаш Telegram ID: <code>{uid}</code>")
    return False

def command_args(text: str) -> str:
    parts = (text or "").split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""

def find_supported_city(raw: str) -> str | None:
    raw = " ".join((raw or "").strip().split()).lower()
    for city in ALL_CITIES:
        if city.lower() == raw:
            return city
    return None

def get_about_text() -> str:
    with db() as con:
        row = con.execute("SELECT value FROM settings WHERE key='about_text'").fetchone()
    return row["value"] if row else "🛒 Это автоматический маркетплейс.\nОплата только в криптовалюте.\nКошельки действительны 30 минут."

def set_about_text(text: str):
    with db() as con:
        con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('about_text', ?)", (text,))
        con.commit()

def all_products():
    with db() as con:
        rows = con.execute("SELECT name, price, group_name, sort_order FROM products ORDER BY sort_order, rowid").fetchall()
    return [dict(r) for r in rows]

def group_counts():
    rows = all_products()
    return (
        sum(1 for r in rows if r["group_name"] == "main"),
        sum(1 for r in rows if r["group_name"] == "extra"),
    )

def product_pid(name: str, group: str) -> str:
    import hashlib
    return hashlib.blake2s(f"{group}:{name}".encode("utf-8"), digest_size=4).hexdigest()

def current_catalog(city: str):
    rows = all_products()
    mains = [r for r in rows if r["group_name"] == "main"][:5]
    extras = [r for r in rows if r["group_name"] == "extra"]
    selected = []
    if extras:
        if len(extras) <= 6:
            selected = extras
        else:
            seed = city + "|" + "|".join(f"{r['name']}:{r['price']}" for r in extras)
            rnd = random.Random(seed)
            selected = rnd.sample(extras, rnd.randint(3, 6))
    out = []
    for r in mains + selected:
        out.append({
            "pid": product_pid(r["name"], r["group_name"]),
            "name": r["name"],
            "price": int(r["price"]),
            "group": r["group_name"],
        })
    return out

def resolve_item(city: str, pid_or_index: str):
    catalog = current_catalog(city)
    for item in catalog:
        if item["pid"] == pid_or_index:
            return item
    if str(pid_or_index).isdigit():
        idx = int(pid_or_index)
        if 0 <= idx < len(catalog):
            return catalog[idx]
    return None

def add_product(name: str, price: int):
    rows = all_products()
    existing = next((r for r in rows if r["name"].lower() == name.lower()), None)
    now = time.time()
    with db() as con:
        if existing:
            con.execute("UPDATE products SET price=?, updated_at=? WHERE lower(name)=lower(?)", (price, now, name))
            group = "основные" if existing["group_name"] == "main" else "дополнительные"
        else:
            main_count = sum(1 for r in rows if r["group_name"] == "main")
            group_name = "main" if main_count < 5 else "extra"
            sort_order = len(rows) + 1
            con.execute(
                "INSERT INTO products(name, price, group_name, sort_order, updated_at) VALUES(?,?,?,?,?)",
                (name, price, group_name, sort_order, now),
            )
            group = "основные" if group_name == "main" else "дополнительные"
        con.commit()
    return group

def delete_product(name: str) -> bool:
    with db() as con:
        cur = con.execute("DELETE FROM products WHERE lower(name)=lower(?)", (name,))
        con.commit()
    return cur.rowcount > 0

def clear_products():
    with db() as con:
        con.execute("DELETE FROM products")
        con.commit()

def products_info_text() -> str:
    rows = all_products()
    mains = [r for r in rows if r["group_name"] == "main"]
    extras = [r for r in rows if r["group_name"] == "extra"]
    lines = [f"📦 <b>Весь товар с ценами</b> — всего: <b>{len(rows)}</b>\n"]
    lines.append(f"<b>Основные товары ({len(mains)}):</b>")
    lines += [f"• {escape(r['name'])} — <b>{r['price']} ₽</b>" for r in mains] or ["нет товаров"]
    lines.append("")
    lines.append(f"<b>Дополнительные товары ({len(extras)}):</b>")
    lines += [f"• {escape(r['name'])} — <b>{r['price']} ₽</b>" for r in extras] or ["нет товаров"]
    return "\n".join(lines)

def add_wallet(t: str, address: str):
    with db() as con:
        con.execute("INSERT INTO wallets(type,address,created_at) VALUES(?,?,?)", (t, address, time.time()))
        con.commit()

def get_wallets(t: str):
    with db() as con:
        rows = con.execute("SELECT address FROM wallets WHERE type=? ORDER BY id", (t,)).fetchall()
    return [r["address"] for r in rows]

def clear_wallets(t: str | None = None):
    with db() as con:
        if t:
            con.execute("DELETE FROM wallets WHERE type=?", (t,))
        else:
            con.execute("DELETE FROM wallets")
        con.commit()

def wallets_text(t: str) -> str:
    items = get_wallets(t)
    return "\n".join(f"• <code>{escape(w)}</code>" for w in items) if items else "не задан"

def random_wallet(t: str) -> str:
    items = get_wallets(t)
    return random.choice(items) if items else "не задан"

def get_districts(city: str, pid: str) -> list[str]:
    if city in TOP_CITIES:
        return (LOCATIONS.get(city) or GENERIC_TOP_DISTRICTS)[:5]
    rnd = random.Random(f"{city}:{pid}")
    return rnd.sample(FALLBACK_DISTRICTS, rnd.randint(2, 4))

def get_rates() -> dict:
    if not USE_LIVE_RATES:
        return {"btc": BTC_RATE, "usdt": USDT_RATE, "ton": TON_RATE}
    now = time.time()
    if _rates_cache["rates"] and now - _rates_cache["ts"] < 300:
        return _rates_cache["rates"]
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,tether,the-open-network&vs_currencies=rub"
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        rates = {
            "btc": float(data["bitcoin"]["rub"]),
            "usdt": float(data["tether"]["rub"]),
            "ton": float(data["the-open-network"]["rub"]),
        }
        _rates_cache.update({"ts": now, "rates": rates})
        return rates
    except Exception:
        return {"btc": BTC_RATE, "usdt": USDT_RATE, "ton": TON_RATE}

def fmt_amount(v: float, decimals: int) -> str:
    return f"{v:.{decimals}f}".rstrip("0").rstrip(".")

def crypto_amounts(rub: int):
    rates = get_rates()
    return (
        fmt_amount(rub / rates["btc"], 8),
        fmt_amount(rub / rates["usdt"], 2),
        fmt_amount(rub / rates["ton"], 3),
        rates,
    )

def main_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="🏙 Выбрать город")],
        [KeyboardButton(text="📦 Мой заказ")],
        [KeyboardButton(text="💰 Проверить оплату")],
        [KeyboardButton(text="ℹ️ О боте")],
        [KeyboardButton(text="🆘 Помощь/Поддержка")],
    ])

def city_keyboard():
    rows = [[InlineKeyboardButton(text=c, callback_data=f"city:{CITY_CODES[c]}")] for c in ALL_CITIES[:15]]
    rows.append([InlineKeyboardButton(text="🔎 Другой город", callback_data="other_city")])
    rows.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def products_keyboard(city: str):
    cc = CITY_CODES.get(city, "0")
    rows = [[InlineKeyboardButton(text=f"{x['name']} — {x['price']} ₽", callback_data=f"prod:{cc}:{x['pid']}")] for x in current_catalog(city)]
    rows.append([InlineKeyboardButton(text="🔙 Города", callback_data="city_menu"), InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def districts_keyboard(city: str, pid: str):
    cc = CITY_CODES.get(city, "0")
    districts = get_districts(city, pid)
    rows = [[InlineKeyboardButton(text=d, callback_data=f"dist:{cc}:{pid}:{i}")] for i, d in enumerate(districts)]
    rows.append([InlineKeyboardButton(text="🔙 Товары", callback_data=f"back:{cc}"), InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def payment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")],
    ])

async def show_city_menu(target, state: FSMContext):
    await state.clear()
    await target.answer("🏙 Выберите город:", reply_markup=city_keyboard())

async def show_products(target, state: FSMContext, city: str):
    await state.update_data(city=city)
    catalog = current_catalog(city)
    if not catalog:
        m, e = group_counts()
        await target.answer(
            "📦 Товары не добавлены или не загружены.\n"
            f"Основные: <b>{m}</b>, дополнительные: <b>{e}</b>\n"
            "Проверьте /add info и /debug."
        )
        return
    await target.answer(f"📍 Город: <b>{escape(city)}</b>\n\n🛍 Выберите товар:", reply_markup=products_keyboard(city))

@dp.message(Command("start"))
async def start_cmd(m: types.Message, state: FSMContext):
    if m.from_user and not ADMIN_IDS:
        ADMIN_IDS.add(m.from_user.id)
        save_admin_ids()
    await state.clear()
    await m.answer("🏪 Добро пожаловать в Маркетплейс", reply_markup=main_kb())

@dp.message(Command("adminid"))
async def adminid_cmd(m: types.Message):
    uid = m.from_user.id if m.from_user else None
    await m.answer(f"Ваш Telegram ID: <code>{uid}</code>\nСтатус: {'✅ админ' if is_admin(uid) else '⛔ не админ'}")

@dp.message(Command("help"))
async def help_cmd(m: types.Message):
    if not await admin_only(m): return
    await m.answer(
        "/add товар цена — добавить\n/add info — список\n/del all — удалить всё\n"
        "/cash btc адрес — добавить BTC\n/cash usdt адрес — добавить USDT\n/cash ton адрес — добавить TON\n"
        "/cash info — кошельки\n/rates — курсы\n/debug — проверка"
    )

@dp.message(Command("debug"))
async def debug_cmd(m: types.Message):
    if not await admin_only(m): return
    mcnt, ecnt = group_counts()
    await m.answer(
        f"DB: <code>{escape(DB_PATH)}</code>\n"
        f"Основные: <b>{mcnt}</b>\nДополнительные: <b>{ecnt}</b>\n"
        f"BTC/USDT/TON кошельки: <b>{len(get_wallets('btc'))}/{len(get_wallets('usdt'))}/{len(get_wallets('ton'))}</b>"
    )

@dp.message(Command("rates"))
async def rates_cmd(m: types.Message):
    if not await admin_only(m): return
    r = get_rates()
    await m.answer(f"BTC: <b>{r['btc']}</b> RUB\nUSDT: <b>{r['usdt']}</b> RUB\nTON: <b>{r['ton']}</b> RUB\nLive: <b>{USE_LIVE_RATES}</b>")

@dp.message(Command("save"))
async def save_cmd(m: types.Message):
    if not await admin_only(m): return
    await m.answer("✅ SQLite сохраняет данные автоматически.")

@dp.message(Command("load"))
async def load_cmd(m: types.Message):
    if not await admin_only(m): return
    await m.answer("✅ SQLite загружает данные автоматически.")

@dp.message(F.text.regexp(r"^/add(@\w+)?(\s|$)"))
async def add_cmd(m: types.Message, state: FSMContext):
    if not await admin_only(m): return
    await state.clear()
    rest = command_args(m.text)
    if rest.lower() == "info":
        await m.answer(products_info_text())
        return
    if not rest or len(rest.split()) < 2:
        await m.answer("❌ Формат: <code>/add Книга 5000</code>")
        return
    name, price_text = rest.rsplit(maxsplit=1)
    if not price_text.isdigit() or int(price_text) <= 0:
        await m.answer("❌ Цена должна быть числом больше 0.")
        return
    name = name.strip().capitalize()
    group = add_product(name, int(price_text))
    mcnt, ecnt = group_counts()
    await m.answer(f"✅ Товар сохранён: <b>{escape(name)}</b> — <b>{int(price_text)} ₽</b>\nРаздел: <b>{group}</b>\nОсновные: <b>{mcnt}</b>, дополнительные: <b>{ecnt}</b>")

@dp.message(F.text.regexp(r"^/(del|dell)(@\w+)?(\s|$)"))
async def del_cmd(m: types.Message, state: FSMContext):
    if not await admin_only(m): return
    arg = command_args(m.text)
    if not arg:
        await m.answer("❌ Формат: <code>/del товар</code> или <code>/del all</code>")
        return
    if arg.lower() == "all":
        clear_products()
        await state.clear()
        await m.answer("✅ Весь товар удалён вместе с ценами.")
        return
    ok = delete_product(arg)
    await state.clear()
    await m.answer(f"✅ Удалено: <b>{escape(arg)}</b>" if ok else "❌ Такой товар не найден.")

@dp.message(F.text.regexp(r"^/cash(@\w+)?(\s|$)"))
async def cash_cmd(m: types.Message, state: FSMContext):
    if not await admin_only(m): return
    args = command_args(m.text)
    parts = args.split(maxsplit=1)
    if not parts or parts[0].lower() == "info":
        await m.answer(f"BTC:\n{wallets_text('btc')}\n\nUSDT:\n{wallets_text('usdt')}\n\nTON:\n{wallets_text('ton')}")
        return
    action = parts[0].lower()
    if action == "del":
        target = parts[1].lower().strip() if len(parts) > 1 else ""
        if target == "all":
            clear_wallets(None)
        elif target in WALLETS:
            clear_wallets(target)
        else:
            await m.answer("❌ /cash del btc|usdt|ton|all")
            return
        await m.answer("✅ Кошельки удалены.")
        return
    if action not in WALLETS:
        await m.answer("❌ Формат: /cash btc адрес, /cash usdt адрес, /cash ton адрес")
        return
    if len(parts) > 1 and parts[1].strip():
        add_wallet(action, parts[1].strip())
        await state.clear()
        await m.answer(f"✅ Кошелёк {WALLET_TITLES[action]} добавлен. Всего: <b>{len(get_wallets(action))}</b>")
        return
    await state.update_data(cash_type=action)
    await state.set_state(S.cash_wallet)
    await m.answer(f"✍️ Отправьте адрес кошелька {WALLET_TITLES[action]}.")

@dp.message(F.text.regexp(r"^/info(@\w+)?\s+"))
async def info_cmd(m: types.Message):
    if not await admin_only(m): return
    set_about_text(command_args(m.text))
    await m.answer("✅ Текст «О боте» изменён.")

@dp.message(F.text.contains("Выбрать город"))
async def choose_city_btn(m: types.Message, state: FSMContext):
    await show_city_menu(m, state)

@dp.message(F.text.contains("Мой заказ"))
async def my_order(m: types.Message):
    await m.answer("📦 У вас ещё нет покупок, сначала произведите оплату.")

@dp.message(F.text.contains("Проверить оплату"))
async def check_payment_btn(m: types.Message):
    await m.answer("💰 Отправьте номер заказа из 7 цифр.")

@dp.message(F.text.contains("О боте"))
async def about_btn(m: types.Message):
    await m.answer(get_about_text())

@dp.message(F.text.contains("Помощь"))
async def support_btn(m: types.Message, state: FSMContext):
    await state.set_state(S.support_message)
    await m.answer("🆘 Напишите сообщение в поддержку одним сообщением.")

@dp.message(S.support_message)
async def support_input(m: types.Message, state: FSMContext):
    if (m.text or "").startswith("/"):
        await state.clear()
        await m.answer("❌ Обращение отменено.")
        return
    await state.clear()
    await m.answer("✅ Ваш запрос будет рассмотрен в течение 1-3 дней, ожидайте, вам придёт ответ, не повторяйте ваш запрос несколько раз.")

@dp.message(S.cash_wallet)
async def cash_wallet_input(m: types.Message, state: FSMContext):
    if not await admin_only(m): return
    data = await state.get_data()
    t = data.get("cash_type")
    wallet = (m.text or "").strip()
    if t not in WALLETS or not wallet:
        await state.clear()
        await m.answer("❌ Повторите /cash.")
        return
    add_wallet(t, wallet)
    await state.clear()
    await m.answer(f"✅ Кошелёк {WALLET_TITLES[t]} добавлен. Всего: <b>{len(get_wallets(t))}</b>")

@dp.message(S.city_name)
async def city_name_input(m: types.Message, state: FSMContext):
    city = find_supported_city(m.text or "")
    if not city:
        await m.answer("❌ Нет такого города. Проверьте название и попробуйте ещё раз.")
        return
    await state.clear()
    await show_products(m, state, city)

@dp.callback_query(F.data == "menu")
async def cb_menu(c: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.answer("🏪 Главное меню", reply_markup=main_kb())

@dp.callback_query(F.data.in_({"city_menu", "city"}))
async def cb_city_menu(c: types.CallbackQuery, state: FSMContext):
    await show_city_menu(c.message, state)

@dp.callback_query(F.data == "other_city")
async def cb_other_city(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(S.city_name)
    await c.message.answer("✍️ Напишите название города в чат.")

@dp.callback_query(F.data.startswith("city:"))
async def cb_city(c: types.CallbackQuery, state: FSMContext):
    code = c.data.split(":", 1)[1]
    city = CODE_CITIES.get(code)
    if not city:
        await show_city_menu(c.message, state)
        return
    await show_products(c.message, state, city)

@dp.callback_query(F.data.startswith("c:"))
async def cb_city_old(c: types.CallbackQuery, state: FSMContext):
    code = c.data.split(":", 1)[1]
    city = CODE_CITIES.get(code)
    if not city:
        await show_city_menu(c.message, state)
        return
    await show_products(c.message, state, city)

@dp.callback_query(F.data.startswith("prod:"))
async def cb_product(c: types.CallbackQuery, state: FSMContext):
    try:
        _, cc, pid = c.data.split(":", 2)
    except Exception:
        await c.answer("Кнопка устарела.", show_alert=True); return
    city = CODE_CITIES.get(cc)
    if not city:
        await show_city_menu(c.message, state); return
    item = resolve_item(city, pid)
    if not item:
        await c.answer("Товар устарел или удалён.", show_alert=True)
        await show_products(c.message, state, city); return
    await state.update_data(city=city)
    await c.message.answer(
        f"📍 {escape(city)}\n🛍 Товар: <b>{escape(item['name'])}</b> — <b>{item['price']} ₽</b>\n\nВыберите район:",
        reply_markup=districts_keyboard(city, pid),
    )

@dp.callback_query(F.data.startswith("p:"))
async def cb_product_old(c: types.CallbackQuery, state: FSMContext):
    try:
        _, cc, value = c.data.split(":", 2)
    except Exception:
        await c.answer("Кнопка устарела.", show_alert=True); return
    city = CODE_CITIES.get(cc)
    if not city:
        await show_city_menu(c.message, state); return
    item = resolve_item(city, value)
    if not item:
        await c.answer("Товар устарел или удалён.", show_alert=True)
        await show_products(c.message, state, city); return
    await state.update_data(city=city)
    await c.message.answer(
        f"📍 {escape(city)}\n🛍 Товар: <b>{escape(item['name'])}</b> — <b>{item['price']} ₽</b>\n\nВыберите район:",
        reply_markup=districts_keyboard(city, item["pid"]),
    )

@dp.callback_query(F.data.startswith("back:"))
async def cb_back_products(c: types.CallbackQuery, state: FSMContext):
    cc = c.data.split(":", 1)[1]
    city = CODE_CITIES.get(cc) or (await state.get_data()).get("city")
    if city:
        await show_products(c.message, state, city)
    else:
        await show_city_menu(c.message, state)

@dp.callback_query(F.data.startswith("dist:"))
async def cb_dist(c: types.CallbackQuery, state: FSMContext):
    try:
        _, cc, pid, idx_text = c.data.split(":", 3)
        idx = int(idx_text)
    except Exception:
        await c.answer("Кнопка устарела.", show_alert=True); return
    city = CODE_CITIES.get(cc)
    if not city:
        await show_city_menu(c.message, state); return
    item = resolve_item(city, pid)
    if not item:
        await c.answer("Товар удалён или устарел.", show_alert=True)
        await show_products(c.message, state, city); return
    districts = get_districts(city, pid)
    if idx < 0 or idx >= len(districts):
        await c.answer("Район устарел.", show_alert=True); return
    district = districts[idx]
    order_id = random.randint(1000000, 9999999)
    btc, usdt, ton, rates = crypto_amounts(int(item["price"]))
    await state.update_data(order_id=order_id, t=time.time(), city=city, product=item["name"], price=item["price"], district=district)
    await c.message.answer(
        f"🆔 <b>Заказ №{order_id}</b>\n\n"
        f"Товар: <b>{escape(item['name'])}</b>\n"
        f"Город: <b>{escape(city)}</b>\n"
        f"Район: <b>{escape(district)}</b>\n\n"
        f"Сумма: <b>{item['price']} ₽</b>\n\n"
        f"🔹 BTC: <code>{btc}</code> → {escape(random_wallet('btc'))}\n"
        f"🔹 USDT-(TRC20): <code>{usdt}</code> → {escape(random_wallet('usdt'))}\n"
        f"🔹 TON: <code>{ton}</code> → {escape(random_wallet('ton'))}\n\n"
        "⏰ Кошельки и сумма актуальны 30 минут.",
        reply_markup=payment_keyboard(),
    )
    asyncio.create_task(reminder(c.from_user.id, order_id))

@dp.callback_query(F.data == "check")
async def cb_check(c: types.CallbackQuery, state: FSMContext):
    await c.answer("⛔ По данному заказу оплата не была получена.", show_alert=True)

@dp.callback_query()
async def cb_unknown(c: types.CallbackQuery):
    await c.answer("Кнопка устарела. Откройте меню заново.", show_alert=True)

async def reminder(user_id: int, order_id: int):
    await asyncio.sleep(20 * 60)
    try:
        await bot.send_message(user_id, f"⏳ Заказ №{order_id}\n\nВаша бронь действительна ещё 10 минут.")
    except Exception:
        pass

@dp.message(F.text.regexp(r"^\d+$"))
async def order_number(m: types.Message):
    await m.answer("⛔ По данному заказу оплата не была получена.")

@dp.message(F.text.startswith("/"))
async def unknown(m: types.Message):
    await m.answer("❌ Неизвестная команда. Используйте /help" if is_admin(m.from_user.id if m.from_user else None) else "⛔ Эта команда доступна только администратору бота.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
