import asyncio
import json
import logging
import os
import random
import re
import time
import urllib.request
from html import escape

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

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

DATA_SAVE_FILE = os.getenv("DATA_SAVE_FILE", "/data/bot_saved_data.json" if os.path.exists("/data") else "bot_saved_data.json")
LOCAL_SAVE_FILE = "bot_saved_data.json"
ADMIN_FILE = "admin_ids.json"

HARD_ADMIN_IDS = [5172121123]

PRODUCTS: dict[str, int] = {}
EXTRA_PRODUCTS: dict[str, int] = {}
WALLETS = {"btc": [], "usdt": [], "ton": []}
WALLET_TITLES = {"btc": "BTC", "usdt": "USDT-(TRC20)", "ton": "TON"}
ABOUT_TEXT = "🛒 Это автоматический маркетплейс.\nОплата только в криптовалюте.\nКошельки действительны 30 минут."

# Резервные курсы в рублях за 1 монету. Можно менять в Railway Variables.
BTC_RATE = float(os.getenv("BTC_RATE", "9500000"))
USDT_RATE = float(os.getenv("USDT_RATE", os.getenv("USDT_TRC20_RATE", "90")))
TON_RATE = float(os.getenv("TON_RATE", "270"))
USE_LIVE_RATES = os.getenv("USE_LIVE_RATES", "1").strip() != "0"
_rates_cache = {"ts": 0.0, "rates": None}

ORDER_DRAFTS: dict[str, dict] = {}

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

def normalize_wallets():
    for k, v in list(WALLETS.items()):
        if isinstance(v, str):
            WALLETS[k] = [v] if v.strip() else []
        else:
            WALLETS[k] = [str(x).strip() for x in v if str(x).strip()]

def save_bot_data():
    normalize_wallets()
    data = {
        "products": PRODUCTS,
        "extra_products": EXTRA_PRODUCTS,
        "wallets": WALLETS,
        "about_text": ABOUT_TEXT,
        "saved_at": time.time(),
    }

    # Пишем во все возможные файлы, чтобы Railway/local не расходились.
    paths = []
    for path in [DATA_SAVE_FILE, LOCAL_SAVE_FILE, "/data/bot_saved_data.json", "bot_saved_data.json"]:
        if path not in paths:
            paths.append(path)

    saved_any = False
    for path in paths:
        try:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            saved_any = True
        except Exception as e:
            logging.warning("save failed %s: %s", path, e)

    if not saved_any:
        raise RuntimeError("Не удалось сохранить данные ни в один файл")

def load_bot_data() -> bool:
    global ABOUT_TEXT

    paths = []
    for path in [DATA_SAVE_FILE, LOCAL_SAVE_FILE, "/data/bot_saved_data.json", "bot_saved_data.json"]:
        if path not in paths and os.path.exists(path):
            paths.append(path)

    candidates = []
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            saved_at = float(data.get("saved_at", os.path.getmtime(path)))
            candidates.append((saved_at, path, data))
        except Exception as e:
            logging.warning("load failed %s: %s", path, e)

    if not candidates:
        return False

    # Берём самый свежий файл. Это исправляет ситуацию, когда старый /data файл пустой,
    # а новый товар был сохранён в локальный bot_saved_data.json.
    candidates.sort(key=lambda x: x[0], reverse=True)
    _, path, data = candidates[0]

    PRODUCTS.clear()
    PRODUCTS.update({str(k): int(v) for k, v in data.get("products", {}).items()})

    EXTRA_PRODUCTS.clear()
    EXTRA_PRODUCTS.update({str(k): int(v) for k, v in data.get("extra_products", {}).items()})

    wallets = data.get("wallets", {})
    for k in WALLETS:
        v = wallets.get(k, [])
        if isinstance(v, str):
            v = [v] if v.strip() else []
        WALLETS[k] = [str(x).strip() for x in v if str(x).strip()]

    ABOUT_TEXT = str(data.get("about_text", ABOUT_TEXT))
    logging.info("loaded data from %s products=%s extra=%s", path, len(PRODUCTS), len(EXTRA_PRODUCTS))
    return True

load_bot_data()

def command_args(text: str) -> str:
    parts = (text or "").split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""

def find_supported_city(raw: str) -> str | None:
    raw = " ".join((raw or "").strip().split()).lower()
    for city in ALL_CITIES:
        if city.lower() == raw:
            return city
    return None

def product_pid(name: str, group: str) -> str:
    # короткий стабильный id без кириллицы и без длинных callback_data
    import hashlib
    return hashlib.blake2s(f"{group}:{name}".encode("utf-8"), digest_size=4).hexdigest()

def current_catalog(city: str) -> list[dict]:
    items = []
    for name, price in list(PRODUCTS.items())[:5]:
        items.append({"pid": product_pid(name, "main"), "name": name, "price": int(price)})

    if EXTRA_PRODUCTS:
        names = list(EXTRA_PRODUCTS.keys())
        if len(names) <= 6:
            selected = names
        else:
            rnd = random.Random(f"{city}|{','.join(names)}|{','.join(str(EXTRA_PRODUCTS[n]) for n in names)}")
            selected = rnd.sample(names, rnd.randint(3, 6))
        for name in selected:
            items.append({"pid": product_pid(name, "extra"), "name": name, "price": int(EXTRA_PRODUCTS[name])})
    return items

def has_products() -> bool:
    return bool(PRODUCTS or EXTRA_PRODUCTS)

def get_city_districts(city: str) -> list[str]:
    if city in TOP_CITIES:
        return (LOCATIONS.get(city) or GENERIC_TOP_DISTRICTS)[:5]
    return random.sample(FALLBACK_DISTRICTS, random.randint(2, 4))

def products_info_text() -> str:
    total = len(PRODUCTS) + len(EXTRA_PRODUCTS)
    lines = [f"📦 <b>Весь товар с ценами</b> — всего: <b>{total}</b>\n"]
    lines.append(f"<b>Основные товары ({len(PRODUCTS)}):</b>")
    lines += [f"• {escape(n)} — <b>{p} ₽</b>" for n, p in PRODUCTS.items()] or ["нет товаров"]
    lines.append("")
    lines.append(f"<b>Дополнительные товары ({len(EXTRA_PRODUCTS)}):</b>")
    lines += [f"• {escape(n)} — <b>{p} ₽</b>" for n, p in EXTRA_PRODUCTS.items()] or ["нет товаров"]
    return "\n".join(lines)


def resolve_catalog_item(city: str, value: str):
    catalog = current_catalog(city)
    found = next((x for x in catalog if x["pid"] == value), None)
    if found:
        return found
    if value.isdigit():
        idx = int(value)
        if 0 <= idx < len(catalog):
            return catalog[idx]
    return None

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
    except Exception as e:
        logging.warning("live rates failed, fallback used: %s", e)
        return {"btc": BTC_RATE, "usdt": USDT_RATE, "ton": TON_RATE}

def fmt_amount(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}".rstrip("0").rstrip(".")

def crypto_amounts(rub: int):
    rates = get_rates()
    return (
        fmt_amount(rub / rates["btc"], 8),
        fmt_amount(rub / rates["usdt"], 2),
        fmt_amount(rub / rates["ton"], 3),
        rates,
    )

def get_random_wallet(t: str) -> str:
    normalize_wallets()
    items = WALLETS.get(t, [])
    return random.choice(items) if items else "не задан"

def wallets_text(t: str) -> str:
    normalize_wallets()
    items = WALLETS.get(t, [])
    return "\n".join(f"• <code>{escape(w)}</code>" for w in items) if items else "не задан"

def main_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="🏙 Выбрать город")],
        [KeyboardButton(text="📦 Мой заказ")],
        [KeyboardButton(text="💰 Проверить оплату")],
        [KeyboardButton(text="ℹ️ О боте")],
        [KeyboardButton(text="🆘 Помощь/Поддержка")],
    ])

def city_keyboard():
    rows = [[InlineKeyboardButton(text=city, callback_data=f"city:{CITY_CODES[city]}")] for city in ALL_CITIES[:15]]
    rows.append([InlineKeyboardButton(text="🔎 Другой город", callback_data="other_city")])
    rows.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def products_keyboard(city: str):
    cc = CITY_CODES.get(city, "0")
    rows = [[InlineKeyboardButton(text=f"{x['name']} — {x['price']} ₽", callback_data=f"prod:{cc}:{x['pid']}")] for x in current_catalog(city)]
    rows.append([InlineKeyboardButton(text="🔙 Города", callback_data="city_menu"), InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def districts_keyboard(draft_id: str, districts: list[str]):
    rows = [[InlineKeyboardButton(text=d, callback_data=f"dist:{draft_id}:{i}")] for i, d in enumerate(districts)]
    rows.append([InlineKeyboardButton(text="🔙 Товары", callback_data=f"back_products:{draft_id}"), InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def payment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")],
    ])

async def send_city_menu(target, state: FSMContext):
    await state.clear()
    await target.answer("🏙 Выберите город:", reply_markup=city_keyboard())

async def send_products(target, state: FSMContext, city: str):
    # Перед показом товаров перечитываем сохранение, чтобы город видел свежие /add.
    load_bot_data()
    await state.update_data(city=city)
    catalog = current_catalog(city)
    if not catalog:
        await target.answer(
            "📦 Товары не добавлены или не загружены.\n"
            f"Основные: <b>{len(PRODUCTS)}</b>, дополнительные: <b>{len(EXTRA_PRODUCTS)}</b>\n"
            "Админ может проверить /add info и /debug."
        )
        return
    await target.answer(f"📍 Город: <b>{escape(city)}</b>\n\n🛍 Выберите товар:", reply_markup=products_keyboard(city))

@dp.message(Command("start"))
async def start_cmd(m: types.Message, state: FSMContext):
    if m.from_user:
        uid = int(m.from_user.id)
        if not ADMIN_IDS:
            ADMIN_IDS.add(uid)
            save_admin_ids()
        if uid in HARD_ADMIN_IDS:
            ADMIN_IDS.add(uid)
            save_admin_ids()
    await state.clear()
    await m.answer("🏪 Добро пожаловать в Маркетплейс", reply_markup=main_kb())

@dp.message(Command("adminid"))
async def adminid_cmd(m: types.Message):
    uid = m.from_user.id if m.from_user else None
    await m.answer(f"Ваш Telegram ID: <code>{uid}</code>\nСтатус: {'✅ админ' if is_admin(uid) else '⛔ не админ'}")

@dp.message(Command("help"))
async def help_cmd(m: types.Message):
    if not await admin_only(m):
        return
    await m.answer(
        "📋 <b>Команды</b>\n"
        "/add товар цена — добавить товар\n"
        "/add info — все товары\n"
        "/del товар — удалить товар\n"
        "/del all или /dell all — удалить всё\n"
        "/cash info — кошельки\n"
        "/cash btc адрес — добавить BTC\n"
        "/cash usdt адрес — добавить USDT\n"
        "/cash ton адрес — добавить TON\n"
        "/rates — курсы\n"
        "/debug — проверка данных\n"
        "/save — сохранить\n"
        "/load — загрузить"
    )

@dp.message(Command("rates"))
async def rates_cmd(m: types.Message):
    if not await admin_only(m):
        return
    r = get_rates()
    await m.answer(
        "💱 <b>Курсы RUB за 1 монету</b>\n"
        f"BTC: <b>{r['btc']}</b>\n"
        f"USDT: <b>{r['usdt']}</b>\n"
        f"TON: <b>{r['ton']}</b>\n"
        f"Live rates: <b>{USE_LIVE_RATES}</b>"
    )

@dp.message(Command("debug"))
async def debug_cmd(m: types.Message):
    if not await admin_only(m):
        return
    load_bot_data()
    await m.answer(
        f"Основные: <b>{len(PRODUCTS)}</b>\n"
        f"Дополнительные: <b>{len(EXTRA_PRODUCTS)}</b>\n"
        f"Drafts: <b>{len(ORDER_DRAFTS)}</b>\n"
        f"Save file: <code>{escape(DATA_SAVE_FILE)}</code>"
    )

@dp.message(Command("save"))
async def save_cmd(m: types.Message):
    if not await admin_only(m):
        return
    save_bot_data()
    await m.answer("✅ Сохранено.")

@dp.message(Command("load"))
async def load_cmd(m: types.Message):
    if not await admin_only(m):
        return
    await m.answer("✅ Загружено." if load_bot_data() else "❌ Сохранение не найдено.")

@dp.message(F.text.regexp(r"^/add(@\w+)?(\s|$)"))
async def add_cmd(m: types.Message, state: FSMContext):
    if not await admin_only(m):
        return
    await state.clear()
    rest = command_args(m.text)
    if rest.lower() == "info":
        load_bot_data()
        await m.answer(products_info_text())
        return
    if not rest or len(rest.split()) < 2:
        await m.answer("❌ Формат: <code>/add Книга 500</code>")
        return
    name, price_text = rest.rsplit(maxsplit=1)
    if not price_text.isdigit() or int(price_text) <= 0:
        await m.answer("❌ Цена должна быть числом больше 0.")
        return
    name = name.strip().capitalize()
    price = int(price_text)
    key = next((x for x in PRODUCTS if x.lower() == name.lower()), None)
    ekey = next((x for x in EXTRA_PRODUCTS if x.lower() == name.lower()), None)
    if key:
        PRODUCTS[key] = price
        group = "основные"
    elif ekey:
        EXTRA_PRODUCTS[ekey] = price
        group = "дополнительные"
    elif len(PRODUCTS) < 5:
        PRODUCTS[name] = price
        group = "основные"
    else:
        EXTRA_PRODUCTS[name] = price
        group = "дополнительные"
    ORDER_DRAFTS.clear()
    save_bot_data()
    load_bot_data()
    await m.answer(f"✅ Товар сохранён: <b>{escape(name)}</b> — <b>{price} ₽</b>\nРаздел: <b>{group}</b>\nВсего: <b>{len(PRODUCTS)+len(EXTRA_PRODUCTS)}</b>")

@dp.message(F.text.regexp(r"^/(del|dell)(@\w+)?(\s|$)"))
async def del_cmd(m: types.Message, state: FSMContext):
    if not await admin_only(m):
        return
    arg = command_args(m.text)
    if not arg:
        await m.answer("❌ Формат: <code>/del товар</code> или <code>/del all</code>")
        return
    if arg.lower() == "all":
        PRODUCTS.clear()
        EXTRA_PRODUCTS.clear()
        ORDER_DRAFTS.clear()
        save_bot_data()
        await state.clear()
        await m.answer("✅ Весь товар удалён вместе с ценами.")
        return
    deleted = False
    for d in (PRODUCTS, EXTRA_PRODUCTS):
        key = next((x for x in list(d) if x.lower() == arg.lower()), None)
        if key:
            d.pop(key, None)
            deleted = True
    ORDER_DRAFTS.clear()
    save_bot_data()
    await state.clear()
    await m.answer(f"✅ Удалено: <b>{escape(arg)}</b>" if deleted else "❌ Такой товар не найден.")

@dp.message(F.text.regexp(r"^/cash(@\w+)?(\s|$)"))
async def cash_cmd(m: types.Message, state: FSMContext):
    if not await admin_only(m):
        return
    args = command_args(m.text)
    parts = args.split(maxsplit=1)
    if not parts or parts[0].lower() == "info":
        await m.answer(f"BTC:\n{wallets_text('btc')}\n\nUSDT:\n{wallets_text('usdt')}\n\nTON:\n{wallets_text('ton')}")
        return
    action = parts[0].lower()
    if action == "del":
        target = parts[1].lower() if len(parts) > 1 else ""
        if target == "all":
            for k in WALLETS: WALLETS[k] = []
        elif target in WALLETS:
            WALLETS[target] = []
        else:
            await m.answer("❌ /cash del btc|usdt|ton|all")
            return
        save_bot_data()
        await m.answer("✅ Удалено.")
        return
    if action not in WALLETS:
        await m.answer("❌ /cash btc адрес | /cash usdt адрес | /cash ton адрес")
        return
    if len(parts) > 1 and parts[1].strip():
        WALLETS[action].append(parts[1].strip())
        save_bot_data()
        await state.clear()
        await m.answer(f"✅ Кошелёк {WALLET_TITLES[action]} добавлен. Всего: <b>{len(WALLETS[action])}</b>")
        return
    await state.update_data(cash_type=action)
    await state.set_state(S.cash_wallet)
    await m.answer(f"✍️ Отправьте адрес кошелька {WALLET_TITLES[action]}.")

@dp.message(F.text.regexp(r"^/info(@\w+)?\s+"))
async def info_cmd(m: types.Message):
    if not await admin_only(m):
        return
    global ABOUT_TEXT
    ABOUT_TEXT = command_args(m.text)
    save_bot_data()
    await m.answer("✅ Текст «О боте» изменён.")

@dp.message(F.text.contains("Выбрать город"))
async def choose_city_btn(m: types.Message, state: FSMContext):
    await send_city_menu(m, state)

@dp.message(F.text.contains("Мой заказ"))
async def my_order(m: types.Message):
    await m.answer("📦 У вас ещё нет покупок, сначала произведите оплату.")

@dp.message(F.text.contains("Проверить оплату"))
async def check_payment_btn(m: types.Message):
    await m.answer("💰 Отправьте номер заказа из 7 цифр.")

@dp.message(F.text.contains("О боте"))
async def about_btn(m: types.Message):
    await m.answer(ABOUT_TEXT)

@dp.message(F.text.contains("Помощь"))
async def support_btn(m: types.Message, state: FSMContext):
    await state.set_state(S.support_message)
    await m.answer("🆘 Напишите сообщение в поддержку одним сообщением.")

@dp.message(S.support_message)
async def support_input(m: types.Message, state: FSMContext):
    text = m.text or ""
    if text.startswith("/") or "Выбрать город" in text or "Мой заказ" in text or "Проверить оплату" in text or "О боте" in text or "Помощь" in text:
        await state.clear()
        await m.answer("❌ Обращение отменено.")
        return
    await state.clear()
    await m.answer("✅ Ваш запрос будет рассмотрен в течение 1-3 дней, ожидайте, вам придёт ответ, не повторяйте ваш запрос несколько раз.")

@dp.message(S.cash_wallet)
async def cash_wallet_input(m: types.Message, state: FSMContext):
    if not await admin_only(m):
        return
    data = await state.get_data()
    t = data.get("cash_type")
    wallet = (m.text or "").strip()
    if not wallet or t not in WALLETS:
        await state.clear()
        await m.answer("❌ Повторите /cash.")
        return
    WALLETS[t].append(wallet)
    save_bot_data()
    await state.clear()
    await m.answer(f"✅ Кошелёк добавлен. Всего: <b>{len(WALLETS[t])}</b>")

@dp.message(S.city_name)
async def city_name_input(m: types.Message, state: FSMContext):
    city = find_supported_city(m.text or "")
    if not city:
        await m.answer("❌ Нет такого города. Проверьте название и попробуйте ещё раз.")
        return
    await state.clear()
    await send_products(m, state, city)

@dp.callback_query(F.data == "menu")
async def cb_menu(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await state.clear()
    await c.message.answer("🏪 Главное меню", reply_markup=main_kb())

@dp.callback_query(F.data == "city_menu")
async def cb_city_menu(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await send_city_menu(c.message, state)


# Совместимость со старыми inline-кнопками из предыдущих версий.
@dp.callback_query(F.data == "city")
async def cb_city_menu_old(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await send_city_menu(c.message, state)

@dp.callback_query(F.data.startswith("c:"))
async def cb_city_old(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    code = c.data.split(":", 1)[1]
    city = CODE_CITIES.get(code)
    if not city:
        await send_city_menu(c.message, state)
        return
    await send_products(c.message, state, city)

@dp.callback_query(F.data == "other_city")
async def cb_other_city(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await state.set_state(S.city_name)
    await c.message.answer("✍️ Напишите название города в чат.")

@dp.callback_query(F.data.startswith("city:"))
async def cb_city(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    city = CODE_CITIES.get(c.data.split(":", 1)[1])
    if not city:
        await send_city_menu(c.message, state)
        return
    await send_products(c.message, state, city)


@dp.callback_query(F.data.startswith("p:"))
async def cb_product_old(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    try:
        _, cc, value = c.data.split(":", 2)
    except Exception:
        await c.answer("Кнопка устарела.", show_alert=True)
        return

    city = CODE_CITIES.get(cc)
    if not city:
        await send_city_menu(c.message, state)
        return

    load_bot_data()
    item = resolve_catalog_item(city, value)
    if not item:
        await c.answer("Товар устарел или удалён.", show_alert=True)
        await send_products(c.message, state, city)
        return

    districts = get_city_districts(city)
    draft_id = str(random.randint(100000, 999999))
    ORDER_DRAFTS[draft_id] = {"city": city, "item": item, "districts": districts, "created_at": time.time()}
    await state.update_data(city=city, last_draft_id=draft_id)
    await c.message.answer(
        f"📍 {escape(city)}\n🛍 Товар: <b>{escape(item['name'])}</b> — <b>{item['price']} ₽</b>\n\nВыберите район:",
        reply_markup=districts_keyboard(draft_id, districts),
    )

@dp.callback_query(F.data.startswith("prod:"))
async def cb_product(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    try:
        _, cc, pid = c.data.split(":", 2)
    except Exception:
        await c.answer("Кнопка устарела.", show_alert=True)
        return
    city = CODE_CITIES.get(cc)
    if not city:
        await send_city_menu(c.message, state)
        return
    load_bot_data()
    item = resolve_catalog_item(city, pid)
    if not item:
        await c.answer("Товар устарел или удалён.", show_alert=True)
        await send_products(c.message, state, city)
        return
    districts = get_city_districts(city)
    draft_id = str(random.randint(100000, 999999))
    ORDER_DRAFTS[draft_id] = {"city": city, "item": item, "districts": districts, "created_at": time.time()}
    await state.update_data(city=city)
    await c.message.answer(
        f"📍 {escape(city)}\n🛍 Товар: <b>{escape(item['name'])}</b> — <b>{item['price']} ₽</b>\n\nВыберите район:",
        reply_markup=districts_keyboard(draft_id, districts),
    )

@dp.callback_query(F.data.startswith("back_products:"))
async def cb_back_products(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    draft_id = c.data.split(":", 1)[1]
    draft = ORDER_DRAFTS.get(draft_id)
    city = draft["city"] if draft else (await state.get_data()).get("city")
    if city:
        await send_products(c.message, state, city)
    else:
        await send_city_menu(c.message, state)


@dp.callback_query(F.data.startswith("d:"))
async def cb_district_old(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    parts = c.data.split(":")

    # Старый формат d:<draft_id>:<idx>
    if len(parts) == 3 and parts[1] in ORDER_DRAFTS:
        draft_id = parts[1]
        idx_text = parts[2]
        c.data = f"dist:{draft_id}:{idx_text}"
        await cb_district(c, state)
        return

    # Старый формат d:<city_code>:<pid_or_index>:<district_idx>
    if len(parts) == 4:
        _, cc, value, idx_text = parts
        city = CODE_CITIES.get(cc)
        if not city:
            await send_city_menu(c.message, state)
            return

        load_bot_data()
        item = resolve_catalog_item(city, value)
        if not item:
            await c.answer("Товар устарел или удалён.", show_alert=True)
            await send_products(c.message, state, city)
            return

        districts = get_city_districts(city)
        draft_id = str(random.randint(100000, 999999))
        ORDER_DRAFTS[draft_id] = {"city": city, "item": item, "districts": districts, "created_at": time.time()}
        c.data = f"dist:{draft_id}:{idx_text}"
        await cb_district(c, state)
        return

    # Очень старый формат d:<token>:<city_code>:<product_index>:<district_idx>
    if len(parts) == 5:
        _, _token, cc, value, idx_text = parts
        city = CODE_CITIES.get(cc)
        if not city:
            await send_city_menu(c.message, state)
            return

        load_bot_data()
        item = resolve_catalog_item(city, value)
        if not item:
            await c.answer("Товар устарел или удалён.", show_alert=True)
            await send_products(c.message, state, city)
            return

        districts = get_city_districts(city)
        draft_id = str(random.randint(100000, 999999))
        ORDER_DRAFTS[draft_id] = {"city": city, "item": item, "districts": districts, "created_at": time.time()}
        c.data = f"dist:{draft_id}:{idx_text}"
        await cb_district(c, state)
        return

    await c.answer("Кнопка устарела. Выберите товар заново.", show_alert=True)

@dp.callback_query(F.data.startswith("dist:"))
async def cb_district(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    try:
        _, draft_id, idx_text = c.data.split(":", 2)
        idx = int(idx_text)
    except Exception:
        await c.answer("Кнопка устарела.", show_alert=True)
        return
    draft = ORDER_DRAFTS.get(draft_id)
    if not draft:
        await c.answer("Выбор устарел. Выберите товар заново.", show_alert=True)
        return
    if idx < 0 or idx >= len(draft["districts"]):
        await c.answer("Район устарел.", show_alert=True)
        return
    city = draft["city"]
    item = draft["item"]
    load_bot_data()
    fresh_item = resolve_catalog_item(city, item["pid"])
    if not fresh_item:
        await c.answer("Товар удалён. Выберите другой.", show_alert=True)
        await send_products(c.message, state, city)
        return
    item = fresh_item
    district = draft["districts"][idx]
    order_id = random.randint(1000000, 9999999)
    btc, usdt, ton, rates = crypto_amounts(int(item["price"]))
    await state.update_data(order_id=order_id, t=time.time(), city=city, product=item["name"], price=item["price"], district=district)
    await c.message.answer(
        f"🆔 <b>Заказ №{order_id}</b>\n\n"
        f"Товар: <b>{escape(item['name'])}</b>\n"
        f"Город: <b>{escape(city)}</b>\n"
        f"Район: <b>{escape(district)}</b>\n\n"
        f"Сумма: <b>{item['price']} ₽</b>\n\n"
        f"🔹 BTC: <code>{btc}</code> → {escape(get_random_wallet('btc'))}\n"
        f"🔹 USDT-(TRC20): <code>{usdt}</code> → {escape(get_random_wallet('usdt'))}\n"
        f"🔹 TON: <code>{ton}</code> → {escape(get_random_wallet('ton'))}\n\n"
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
