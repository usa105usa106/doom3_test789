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

def load_admin_ids() -> set[int]:
    ids = set()
    for x in HARD_ADMIN_IDS:
        try:
            ids.add(int(x))
        except Exception:
            pass

    for name in ["ADMIN_IDS", "ADMIN_ID", "admin_ids", "admin_id", "amdin_ids", "AMDIN_IDS", "ADMINS"]:
        raw = os.getenv(name, "")
        for part in re.findall(r"\d+", raw):
            ids.add(int(part))

    try:
        if os.path.exists(ADMIN_FILE):
            with open(ADMIN_FILE, "r", encoding="utf-8") as f:
                for x in json.load(f):
                    ids.add(int(x))
    except Exception as e:
        logging.warning("admin load error: %s", e)

    return ids

ADMIN_IDS = load_admin_ids()

def save_admin_ids() -> None:
    try:
        with open(ADMIN_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(ADMIN_IDS), f, ensure_ascii=False)
    except Exception as e:
        logging.warning("admin save error: %s", e)

def is_admin(user_id: int | None) -> bool:
    return user_id is not None and int(user_id) in ADMIN_IDS

async def admin_only(m: types.Message) -> bool:
    uid = m.from_user.id if m.from_user else None
    if is_admin(uid):
        return True
    await m.answer(
        "⛔ Эта команда доступна только администратору бота.\n"
        f"Ваш Telegram ID: <code>{uid}</code>\n\n"
        "Добавьте этот ID в Railway Variables:\n"
        "<code>ADMIN_IDS=5172121123</code>"
    )
    return False

class S(StatesGroup):
    city_name = State()
    cash_wallet = State()

# ВАЖНО: товары по умолчанию пустые.
# Старые дефолтные товары больше не подгружаются после /del all.
PRODUCTS: dict[str, int] = {}
EXTRA_PRODUCTS: dict[str, int] = {}

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
"Соль-Илецк","Медногорск","Сорочинск","Кувандык","Сызрань","Новокуйбышевск","Чапаевск","Отрадный","Жигулёвск","Кинель","Похвистнево",
"Бор","Арзамас","Саров","Кстово","Павлово","Выкса","Балахна","Заволжье","Городец","Шуя","Кинешма","Вичуга","Фурманов","Тейково",
"Родники","Кольчугино","Александров","Гусь-Хрустальный","Вязники","Рыбинск","Переславль-Залесский","Углич","Тутаев","Ростов Великий",
"Ржев","Вышний Волочёк","Кимры","Торжок","Конаково","Бежецк","Великие Луки","Остров","Печоры","Невель","Старая Русса","Боровичи",
"Валдай","Кириши","Выборг","Гатчина","Сосновый Бор","Тихвин","Всеволожск","Кингисепп","Луга","Сертолово","Волхов","Тосно",
"Пушкин","Колпино","Петергоф","Кронштадт","Ломоносов","Котлас","Новодвинск","Коряжма","Мирный","Онега","Вельск","Нарьян-Мар",
"Апатиты","Североморск","Мончегорск","Кандалакша","Оленегорск","Костомукша","Сортавала","Кондопога","Сегежа","Медвежьегорск",
"Великий Устюг","Сокол","Шексна","Грязовец","Буй","Шарья","Нерехта","Галич","Мантурово","Клин","Дмитров","Солнечногорск",
"Ногинск","Пушкино","Орехово-Зуево","Сергиев Посад","Воскресенск","Лобня","Долгопрудный","Реутов","Дубна","Егорьевск",
"Наро-Фоминск","Чехов","Ступино","Кашира","Видное","Истра","Фрязино","Лыткарино","Дзержинский","Котельники","Луховицы",
"Можайск","Руза","Зарайск","Волоколамск","Клинцы","Новозыбков","Дятьково","Унеча","Севск","Алексин","Ефремов","Узловая",
"Щёкино","Донской","Кимовск","Киреевск","Суворов","Мценск","Ливны","Железногорск","Курчатов","Льгов","Рыльск","Губкин",
"Шебекино","Алексеевка","Валуйки","Строитель","Россошь","Борисоглебск","Лиски","Острогожск","Нововоронеж","Павловск",
"Семилуки","Моршанск","Рассказово","Котовск","Уварово","Кирсанов","Кузнецк","Заречный","Каменка","Сердобск","Нижний Ломов",
"Сасово","Скопин","Касимов","Шацк","Вязьма","Рославль","Сафоново","Ярцево","Гагарин","Десногорск","Людиново","Киров Калужский",
"Малоярославец","Балабаново","Козельск","Кондрово","Ейск","Кропоткин","Анапа","Геленджик","Туапсе","Тихорецк",
"Славянск-на-Кубани","Белореченск","Лабинск","Апшеронск","Горячий Ключ","Крымск","Темрюк","Кореновск","Усть-Лабинск",
"Майкоп","Адыгейск","Черкесск","Карачаевск","Будённовск","Георгиевск","Минеральные Воды","Михайловск","Изобильный",
"Светлоград","Зеленокумск","Лермонтов","Баксан","Прохладный","Моздок","Беслан","Малгобек","Аргун","Гудермес","Шали",
"Урус-Мартан","Кизляр","Буйнакск","Избербаш","Кизилюрт","Дагестанские Огни","Южно-Сухокумск","Волгодонск","Гуково",
"Донецк","Зверево","Миллерово","Морозовск","Сальск","Семикаракорск","Цимлянск","Фролово","Камышин","Михайловка",
"Урюпинск","Котельниково","Калач-на-Дону","Палласовка","Дубовка","Ахтубинск","Знаменск","Харабали","Камызяк","Нариманов",
"Вольск","Балашов","Маркс","Пугачёв","Ртищево","Аткарск","Петровск","Хвалынск","Ершов","Новоузенск","Красноармейск"
]
_seen = set()
ALL_CITIES = [c for c in ALL_CITIES if not (c in _seen or _seen.add(c))]
CITY_CODES = {c: str(i) for i, c in enumerate(ALL_CITIES)}
CODE_CITIES = {str(i): c for i, c in enumerate(ALL_CITIES)}
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

WALLETS = {"btc": [], "usdt": [], "ton": []}
WALLET_TITLES = {"btc": "BTC", "usdt": "USDT-(TRC20)", "ton": "TON"}

BTC_RATE = float(os.getenv("BTC_RATE", "9500000"))
USDT_TRC20_RATE = float(os.getenv("USDT_TRC20_RATE", "90"))
TON_RATE = float(os.getenv("TON_RATE", "270"))
_rates_cache = {"ts": 0, "rates": None}

ABOUT_TEXT = "🛒 Это автоматический маркетплейс.\nОплата только в криптовалюте.\nКошельки действительны 30 минут."

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
        "shop_initialized": True,
    }
    for path in [DATA_SAVE_FILE, LOCAL_SAVE_FILE]:
        try:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.warning("save error %s: %s", path, e)

def load_bot_data() -> bool:
    global ABOUT_TEXT
    for path in [DATA_SAVE_FILE, LOCAL_SAVE_FILE]:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Старые дефолтные товары не восстанавливаются.
        PRODUCTS.clear()
        EXTRA_PRODUCTS.clear()
        PRODUCTS.update({str(k): int(v) for k, v in data.get("products", {}).items()})
        EXTRA_PRODUCTS.update({str(k): int(v) for k, v in data.get("extra_products", {}).items()})

        saved_wallets = data.get("wallets", {})
        for k in WALLETS:
            v = saved_wallets.get(k, [])
            if isinstance(v, str):
                v = [v] if v.strip() else []
            WALLETS[k] = [str(x).strip() for x in v if str(x).strip()]
        ABOUT_TEXT = str(data.get("about_text", ABOUT_TEXT))
        logging.info("data loaded from %s products=%s extra=%s", path, len(PRODUCTS), len(EXTRA_PRODUCTS))
        return True
    return False

try:
    load_bot_data()
except Exception as e:
    logging.warning("auto load failed: %s", e)

def command_args(text: str) -> str:
    parts = (text or "").split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""

def find_supported_city(raw: str) -> str | None:
    raw = " ".join((raw or "").strip().split()).lower()
    for c in ALL_CITIES:
        if c.lower() == raw:
            return c
    return None

def city_products(city: str) -> dict[str, int]:
    result = dict(PRODUCTS)
    if EXTRA_PRODUCTS:
        rnd = random.Random(f"extras:{city}:{len(EXTRA_PRODUCTS)}:{','.join(EXTRA_PRODUCTS.keys())}")
        count = min(rnd.randint(3, 6), len(EXTRA_PRODUCTS))
        for name in rnd.sample(list(EXTRA_PRODUCTS.keys()), count):
            result[name] = EXTRA_PRODUCTS[name]
    return result

def get_city_districts(city: str) -> list[str]:
    if city in TOP_CITIES:
        return (LOCATIONS.get(city) or GENERIC_TOP_DISTRICTS)[:5]
    return random.sample(FALLBACK_DISTRICTS, random.randint(2, 4))

def get_random_wallet(t: str) -> str:
    normalize_wallets()
    wallets = WALLETS.get(t, [])
    return random.choice(wallets) if wallets else "не задан"

def wallets_text(t: str) -> str:
    normalize_wallets()
    wallets = WALLETS.get(t, [])
    return "\n".join(f"• <code>{escape(x)}</code>" for x in wallets) if wallets else "не задан"

def has_products() -> bool:
    return bool(PRODUCTS or EXTRA_PRODUCTS)

def products_info_text() -> str:
    out = ["📦 <b>Весь товар с ценами</b>\n", "<b>Основные товары:</b>"]
    out += [f"• {escape(n)} — <b>{p} ₽</b>" for n, p in PRODUCTS.items()] or ["нет товаров"]
    out += ["", "<b>Дополнительные товары:</b>"]
    out += [f"• {escape(n)} — <b>{p} ₽</b>" for n, p in EXTRA_PRODUCTS.items()] or ["нет товаров"]
    return "\n".join(out)

def fmt_amount(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}".rstrip("0").rstrip(".")

def get_live_rates() -> dict:
    now = time.time()
    if _rates_cache["rates"] and now - _rates_cache["ts"] < 300:
        return _rates_cache["rates"]
    fallback = {"btc": BTC_RATE, "usdt": USDT_TRC20_RATE, "ton": TON_RATE}
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,tether,the-open-network&vs_currencies=rub"
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
        rates = {"btc": float(data["bitcoin"]["rub"]), "usdt": float(data["tether"]["rub"]), "ton": float(data["the-open-network"]["rub"])}
        _rates_cache.update({"ts": now, "rates": rates})
        return rates
    except Exception:
        return fallback

def get_crypto_amounts(rub: int):
    rates = get_live_rates()
    return fmt_amount(rub / rates["btc"], 8), fmt_amount(rub / rates["usdt"], 2), fmt_amount(rub / rates["ton"], 3)

def main_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="🏙 Выбрать город")],
        [KeyboardButton(text="📦 Мой заказ")],
        [KeyboardButton(text="💰 Проверить оплату")],
        [KeyboardButton(text="ℹ️ О боте")],
    ])

def city_keyboard():
    rows = [[InlineKeyboardButton(text=c, callback_data=f"c:{CITY_CODES[c]}")] for c in ALL_CITIES[:15]]
    rows.append([InlineKeyboardButton(text="🔎 Другой город", callback_data="other_city")])
    rows.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def products_keyboard(city: str):
    items = list(city_products(city).items())
    cc = CITY_CODES.get(city, "x")
    rows = [[InlineKeyboardButton(text=f"{n} — {p} ₽", callback_data=f"p:{cc}:{i}")] for i, (n, p) in enumerate(items)]
    rows.append([InlineKeyboardButton(text="🔙 Города", callback_data="city"), InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def districts_keyboard(city: str, product_index: int, districts: list[str], token: str):
    cc = CITY_CODES.get(city, "x")
    rows = [[InlineKeyboardButton(text=d, callback_data=f"d:{token}:{cc}:{product_index}:{i}")] for i, d in enumerate(districts)]
    rows.append([InlineKeyboardButton(text="🔙 Товары", callback_data="back_products"), InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def safe_edit(message: types.Message, text: str, reply_markup=None):
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except Exception:
        await message.answer(text, reply_markup=reply_markup)

async def show_city_menu(message_or_callback_message, state: FSMContext):
    await state.clear()
    await message_or_callback_message.answer("🏙 Выберите город:", reply_markup=city_keyboard())

async def show_products_for_city(message: types.Message, state: FSMContext, city: str, edit: bool = True):
    await state.update_data(city=city)
    if not has_products():
        text = "📦 Товары не добавлены. Админ должен добавить товар командой /add название цена."
        if edit:
            await safe_edit(message, text, reply_markup=city_keyboard())
        else:
            await message.answer(text)
        return
    text = f"📍 Город: <b>{escape(city)}</b>\n\n🛍 Выберите товар:"
    if edit:
        await safe_edit(message, text, reply_markup=products_keyboard(city))
    else:
        await message.answer(text, reply_markup=products_keyboard(city))

# ===================== COMMANDS AND MENU =====================

@dp.message(Command("start"))
async def start_cmd(m: types.Message, state: FSMContext):
    if m.from_user:
        uid = int(m.from_user.id)
        if uid in {int(x) for x in HARD_ADMIN_IDS} and uid not in ADMIN_IDS:
            ADMIN_IDS.add(uid)
            save_admin_ids()
        if not ADMIN_IDS:
            ADMIN_IDS.add(uid)
            save_admin_ids()
            await m.answer(f"✅ Вы назначены администратором.\nВаш Telegram ID: <code>{uid}</code>")
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
        "📋 <b>Команды</b>\n\n"
        "/add товар цена — добавить товар\n"
        "/add info — список товаров\n"
        "/del товар — удалить товар\n"
        "/del all или /dell all — удалить весь товар\n"
        "/info текст — изменить «О боте»\n"
        "/cash info — кошельки\n"
        "/cash btc адрес — добавить BTC\n"
        "/cash usdt адрес — добавить USDT\n"
        "/cash ton адрес — добавить TON\n"
        "/cash del btc|usdt|ton|all — удалить кошельки\n"
        "/save — сохранить\n"
        "/load — загрузить\n"
        "/adminid — проверить ID"
    )

@dp.message(F.text.contains("Выбрать город"))
async def choose_city(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer("🏙 Выберите город:", reply_markup=city_keyboard())

@dp.message(F.text.contains("Мой заказ"))
async def my_order(m: types.Message):
    await m.answer("📦 У вас ещё нет покупок, сначала произведите оплату.")

@dp.message(F.text.contains("Проверить оплату"))
async def check_payment_btn(m: types.Message):
    await m.answer("💰 Отправьте номер заказа из 7 цифр.")

@dp.message(F.text.contains("О боте"))
async def about(m: types.Message):
    await m.answer(ABOUT_TEXT)

@dp.message(Command("save"))
async def save_cmd(m: types.Message):
    if not await admin_only(m):
        return
    save_bot_data()
    await m.answer("✅ Все изменения сохранены.")

@dp.message(Command("load"))
async def load_cmd(m: types.Message):
    if not await admin_only(m):
        return
    if load_bot_data():
        await m.answer("✅ Последние сохранённые значения загружены.")
    else:
        await m.answer("❌ Сохранение не найдено.")

@dp.message(F.text.regexp(r"^/add(@\w+)?(\s|$)"))
async def add_cmd(m: types.Message):
    if not await admin_only(m):
        return
    rest = command_args(m.text)
    if rest.lower() == "info":
        await m.answer(products_info_text())
        return
    if not rest or len(rest.split()) < 2:
        await m.answer("❌ Формат: <code>/add Книга 500</code>")
        return
    name, price_text = rest.rsplit(maxsplit=1)
    if not price_text.isdigit() or int(price_text) <= 0:
        await m.answer("❌ Цена должна быть положительным числом.")
        return
    name = name.strip().capitalize()
    price = int(price_text)
    key = next((x for x in PRODUCTS if x.lower() == name.lower()), None)
    extra_key = next((x for x in EXTRA_PRODUCTS if x.lower() == name.lower()), None)
    if key:
        PRODUCTS[key] = price
        group = "основные товары"
    elif extra_key:
        EXTRA_PRODUCTS[extra_key] = price
        group = "дополнительные товары"
    elif len(PRODUCTS) < 5:
        PRODUCTS[name] = price
        group = "основные товары"
    else:
        EXTRA_PRODUCTS[name] = price
        group = "дополнительные товары"
    save_bot_data()
    await m.answer(f"✅ Товар сохранён: <b>{escape(name)}</b> — <b>{price} ₽</b>\nРаздел: <b>{group}</b>")

@dp.message(F.text.regexp(r"^/(del|dell)(@\w+)?(\s|$)"))
async def del_cmd(m: types.Message, state: FSMContext):
    if not await admin_only(m):
        return
    name = command_args(m.text)
    if not name:
        await m.answer("❌ Формат: <code>/del товар</code> или <code>/del all</code>")
        return
    if name.lower() == "all":
        PRODUCTS.clear()
        EXTRA_PRODUCTS.clear()
        save_bot_data()
        await state.clear()
        await m.answer("✅ Весь товар полностью удалён вместе с ценами.")
        return
    deleted = False
    key = next((x for x in list(PRODUCTS) if x.lower() == name.lower()), None)
    if key:
        PRODUCTS.pop(key, None)
        deleted = True
    key = next((x for x in list(EXTRA_PRODUCTS) if x.lower() == name.lower()), None)
    if key:
        EXTRA_PRODUCTS.pop(key, None)
        deleted = True
    save_bot_data()
    await state.clear()
    await m.answer(f"✅ Товар удалён: <b>{escape(name)}</b>" if deleted else "❌ Такой товар не найден.")

@dp.message(F.text.regexp(r"^/info(@\w+)?\s+"))
async def info_cmd(m: types.Message):
    if not await admin_only(m):
        return
    global ABOUT_TEXT
    ABOUT_TEXT = command_args(m.text)
    save_bot_data()
    await m.answer("✅ Сообщение «О боте» изменено.")

@dp.message(F.text.regexp(r"^/cash(@\w+)?(\s|$)"))
async def cash_cmd(m: types.Message, state: FSMContext):
    if not await admin_only(m):
        return
    args = command_args(m.text)
    parts = args.split(maxsplit=1)
    if not parts or parts[0].lower() == "info":
        await m.answer(
            "💳 <b>Кошельки</b>\n\n"
            f"BTC:\n{wallets_text('btc')}\n\n"
            f"USDT-(TRC20):\n{wallets_text('usdt')}\n\n"
            f"TON:\n{wallets_text('ton')}"
        )
        return
    action = parts[0].lower()
    if action == "del":
        target = parts[1].lower().strip() if len(parts) > 1 else ""
        if target == "all":
            for k in WALLETS:
                WALLETS[k] = []
            save_bot_data()
            await m.answer("✅ Все кошельки удалены.")
            return
        if target in WALLETS:
            WALLETS[target] = []
            save_bot_data()
            await m.answer(f"✅ Кошельки {WALLET_TITLES[target]} удалены.")
            return
        await m.answer("❌ Формат: /cash del btc|usdt|ton|all")
        return
    if action not in WALLETS:
        await m.answer("❌ Формат: /cash btc адрес, /cash usdt адрес, /cash ton адрес")
        return
    if len(parts) > 1 and parts[1].strip():
        wallet = parts[1].strip()
        WALLETS[action].append(wallet)
        save_bot_data()
        await state.clear()
        await m.answer(f"✅ Кошелёк {WALLET_TITLES[action]} добавлен.\nВсего: <b>{len(WALLETS[action])}</b>")
        return
    await state.update_data(cash_type=action)
    await state.set_state(S.cash_wallet)
    await m.answer(f"✍️ Отправьте адрес кошелька {WALLET_TITLES[action]}.")

@dp.message(S.cash_wallet)
async def cash_wallet_input(m: types.Message, state: FSMContext):
    if not await admin_only(m):
        return
    data = await state.get_data()
    t = data.get("cash_type")
    wallet = (m.text or "").strip()
    if t not in WALLETS or not wallet:
        await state.clear()
        await m.answer("❌ Повторите команду /cash.")
        return
    WALLETS[t].append(wallet)
    save_bot_data()
    await state.clear()
    await m.answer(f"✅ Кошелёк {WALLET_TITLES[t]} добавлен.\nВсего: <b>{len(WALLETS[t])}</b>")

# ===================== CALLBACKS =====================

@dp.callback_query(F.data == "menu")
async def cb_menu(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await state.clear()
    await safe_edit(c.message, "🏪 Главное меню")
    await c.message.answer("Выберите действие:", reply_markup=main_kb())

@dp.callback_query(F.data == "city")
async def cb_city(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await state.clear()
    await safe_edit(c.message, "🏙 Выберите город:", reply_markup=city_keyboard())

@dp.callback_query(F.data == "other_city")
async def cb_other_city(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await state.set_state(S.city_name)
    await safe_edit(c.message, "✍️ Напишите название города в чат.")

@dp.callback_query(F.data.startswith("c:"))
async def cb_city_selected(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    city = CODE_CITIES.get(c.data.split(":", 1)[1])
    if not city:
        await safe_edit(c.message, "🏙 Выберите город:", reply_markup=city_keyboard())
        return
    await show_products_for_city(c.message, state, city, edit=True)

@dp.message(S.city_name)
async def city_name_input(m: types.Message, state: FSMContext):
    city = find_supported_city(m.text or "")
    if not city:
        await m.answer("❌ Нет такого города. Проверьте название и попробуйте ещё раз.")
        return
    await show_products_for_city(m, state, city, edit=False)

@dp.callback_query(F.data.startswith("p:"))
async def cb_product(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    try:
        _, cc, idx_text = c.data.split(":", 2)
        idx = int(idx_text)
    except Exception:
        await c.answer("Кнопка устарела.", show_alert=True)
        return
    city = CODE_CITIES.get(cc)
    if not city:
        await safe_edit(c.message, "🏙 Выберите город:", reply_markup=city_keyboard())
        return
    items = list(city_products(city).items())
    if not items:
        await safe_edit(c.message, "📦 Товары не добавлены.", reply_markup=city_keyboard())
        return
    if idx < 0 or idx >= len(items):
        await safe_edit(c.message, f"📍 Город: <b>{escape(city)}</b>\n\n🛍 Выберите товар:", reply_markup=products_keyboard(city))
        return
    product, price = items[idx]
    districts = get_city_districts(city)
    token = str(random.randint(100000, 999999))
    await state.update_data(city=city, product=product, price=price, product_index=idx, districts=districts, order_token=token)
    await safe_edit(
        c.message,
        f"📍 {escape(city)}\n🛍 Товар: <b>{escape(product)}</b> — <b>{price} ₽</b>\n\nВыберите район:",
        reply_markup=districts_keyboard(city, idx, districts, token),
    )

@dp.callback_query(F.data == "back_products")
async def cb_back_products(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    data = await state.get_data()
    city = data.get("city")
    if not city:
        await safe_edit(c.message, "🏙 Выберите город:", reply_markup=city_keyboard())
        return
    await show_products_for_city(c.message, state, city, edit=True)

@dp.callback_query(F.data.startswith("d:"))
async def cb_district(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    data = await state.get_data()
    try:
        _, token, cc, product_idx_text, district_idx_text = c.data.split(":", 4)
        product_idx = int(product_idx_text)
        district_idx = int(district_idx_text)
    except Exception:
        await c.answer("Кнопка устарела.", show_alert=True)
        return
    if token != data.get("order_token"):
        await c.answer("Кнопка устарела. Выберите товар заново.", show_alert=True)
        city = data.get("city")
        if city:
            await show_products_for_city(c.message, state, city, edit=True)
        return
    city = CODE_CITIES.get(cc) or data.get("city")
    districts = data.get("districts") or []
    items = list(city_products(city).items()) if city else []
    if product_idx >= len(items) or district_idx >= len(districts):
        await c.answer("Данные устарели. Выберите товар заново.", show_alert=True)
        if city:
            await show_products_for_city(c.message, state, city, edit=True)
        return
    product, price = items[product_idx]
    district = districts[district_idx]
    order_id = random.randint(1000000, 9999999)
    await state.update_data(order_id=order_id, t=time.time(), product=product, price=price, district=district, city=city)
    btc, usdt, ton = get_crypto_amounts(price)
    text = (
        f"🆔 <b>Заказ №{order_id}</b>\n\n"
        f"Товар: <b>{escape(product)}</b>\n"
        f"Город: <b>{escape(city)}</b>\n"
        f"Район: <b>{escape(district)}</b>\n\n"
        f"Сумма: <b>{price} ₽</b>\n\n"
        f"🔹 BTC: <code>{btc}</code> → {escape(get_random_wallet('btc'))}\n"
        f"🔹 USDT-(TRC20): <code>{usdt}</code> → {escape(get_random_wallet('usdt'))}\n"
        f"🔹 TON: <code>{ton}</code> → {escape(get_random_wallet('ton'))}\n\n"
        "⏰ Внимание!!! Для покупки товара оплатите точную сумму на любой из этих кошельков. "
        "Кошельки и сумма актуальны 30 минут."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")],
    ])
    await safe_edit(c.message, text, reply_markup=kb)
    asyncio.create_task(reminder(c.from_user.id, order_id))

async def reminder(user_id: int, order_id: int):
    await asyncio.sleep(20 * 60)
    try:
        await bot.send_message(user_id, f"⏳ Заказ №{order_id}\n\nВаша бронь действительна ещё 10 минут.")
    except Exception:
        pass

@dp.callback_query(F.data == "check")
async def cb_check(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if time.time() - data.get("t", 0) > 1800:
        await c.answer("⛔ Время на оплату вышло (30 минут)", show_alert=True)
    else:
        await c.answer("⛔ По данному заказу оплата не была получена.", show_alert=True)

@dp.message(F.text.regexp(r"^\d+$"))
async def order_number(m: types.Message):
    digits = m.text.strip()
    if len(digits) == 7:
        await m.answer("⛔ По данному заказу оплата не была получена.")
    else:
        await m.answer("❌ Введите 7 цифр номера заказа.")

@dp.message(F.text.startswith("/"))
async def unknown_command(m: types.Message):
    if is_admin(m.from_user.id if m.from_user else None):
        await m.answer("❌ Неизвестная команда. Используйте /help")
    else:
        await m.answer("⛔ Эта команда доступна только администратору бота.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
