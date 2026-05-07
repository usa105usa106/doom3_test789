import asyncio
import json
import logging
import os
import random
import re
import sqlite3
import time
import urllib.request
import uuid
import base64
from html import escape
from pathlib import Path

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import ErrorEvent
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set")

def resolve_db_path() -> str:
    """
    Один путь к базе для товаров и кошельков.
    На Railway используйте Volume /data. Тогда все команды и кнопки читают одну базу.
    """
    env_path = os.getenv("DB_PATH", "").strip()
    if env_path:
        return env_path
    try:
        os.makedirs("/data", exist_ok=True)
        return "/data/bot.db"
    except Exception:
        return "bot.db"

DB_PATH = resolve_db_path()
ADMIN_FILE = "admin_ids.json"
HARD_ADMIN_IDS = [5172121123]

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

BTC_RATE = float(os.getenv("BTC_RATE", "9500000"))
USDT_RATE = float(os.getenv("USDT_RATE", os.getenv("USDT_TRC20_RATE", "90")))
TON_RATE = float(os.getenv("TON_RATE", "270"))
USE_LIVE_RATES = os.getenv("USE_LIVE_RATES", "1").strip() != "0"
_rates_cache = {"ts": 0.0, "rates": None}
INSTANCE_ID = str(uuid.uuid4())
BOT_START_TIME = time.time()

WALLETS = {"btc", "usdt", "ton"}
WALLET_TITLES = {
    "btc": "BTC",
    "usdt": "USDT",
    "ton": "TON",
}

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
ALL_CITIES = list(dict.fromkeys(ALL_CITIES))[:300]
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
# Для городов после 50-го места показываем только 2-4 случайных варианта из этого списка.
FALLBACK_DISTRICTS = ["Центр", "Автовокзал", "ЖД/вокзал", "Любой район"]
GENERIC_TOP_DISTRICTS = ["Центр", "Ленинский", "Советский", "Октябрьский", "Центральный"]

# Районы для первых 50 крупнейших городов.
LOCATIONS.update({
    "Краснодар": ["Центральный", "Западный", "Карасунский", "Прикубанский", "Фестивальный"],
    "Саратов": ["Волжский", "Кировский", "Ленинский", "Октябрьский", "Фрунзенский"],
    "Тюмень": ["Центральный", "Ленинский", "Калининский", "Восточный", "Заречный"],
    "Тольятти": ["Автозаводский", "Центральный", "Комсомольский", "Новый город", "Старый город"],
    "Ижевск": ["Октябрьский", "Индустриальный", "Ленинский", "Первомайский", "Устиновский"],
    "Барнаул": ["Центральный", "Индустриальный", "Ленинский", "Октябрьский", "Железнодорожный"],
    "Ульяновск": ["Ленинский", "Засвияжский", "Заволжский", "Железнодорожный", "Центр"],
    "Иркутск": ["Правобережный", "Октябрьский", "Свердловский", "Ленинский", "Центр"],
    "Хабаровск": ["Центральный", "Индустриальный", "Железнодорожный", "Кировский", "Краснофлотский"],
    "Ярославль": ["Кировский", "Ленинский", "Фрунзенский", "Красноперекопский", "Дзержинский"],
    "Владивосток": ["Фрунзенский", "Ленинский", "Первомайский", "Первореченский", "Советский"],
    "Махачкала": ["Советский", "Ленинский", "Кировский", "Редукторный", "Центр"],
    "Томск": ["Советский", "Кировский", "Ленинский", "Октябрьский", "Центр"],
    "Оренбург": ["Центральный", "Ленинский", "Промышленный", "Дзержинский", "Степной"],
    "Кемерово": ["Центральный", "Ленинский", "Заводский", "Кировский", "Рудничный"],
    "Новокузнецк": ["Центральный", "Кузнецкий", "Куйбышевский", "Орджоникидзевский", "Заводской"],
    "Рязань": ["Советский", "Железнодорожный", "Московский", "Октябрьский", "Центр"],
    "Астрахань": ["Кировский", "Ленинский", "Советский", "Трусовский", "Центр"],
    "Пенза": ["Ленинский", "Октябрьский", "Первомайский", "Железнодорожный", "Арбеково"],
    "Липецк": ["Советский", "Октябрьский", "Правобережный", "Левобережный", "Центр"],
    "Киров": ["Ленинский", "Октябрьский", "Первомайский", "Нововятский", "Центр"],
    "Чебоксары": ["Ленинский", "Московский", "Калининский", "Северо-Западный", "Новоюжный"],
    "Брянск": ["Советский", "Бежицкий", "Фокинский", "Володарский", "Центр"],
    "Тула": ["Центральный", "Советский", "Пролетарский", "Зареченский", "Привокзальный"],
    "Курск": ["Центральный", "Сеймский", "Железнодорожный", "Северо-Западный", "КЗТЗ"],
    "Ставрополь": ["Ленинский", "Октябрьский", "Промышленный", "Центр", "Перспективный"],
    "Улан-Удэ": ["Советский", "Железнодорожный", "Октябрьский", "Центр", "Восточный"],
    "Тверь": ["Центральный", "Московский", "Пролетарский", "Заволжский", "Южный"],
    "Магнитогорск": ["Правобережный", "Ленинский", "Орджоникидзевский", "Центр", "Новый город"],
    "Сочи": ["Центральный", "Адлерский", "Хостинский", "Лазаревский", "Мамайка"],
    "Иваново": ["Ленинский", "Советский", "Октябрьский", "Фрунзенский", "Центр"],
    "Белгород": ["Западный", "Восточный", "Центр", "Харьковская гора", "Крейда"],
    "Архангельск": ["Октябрьский", "Ломоносовский", "Соломбальский", "Майская Горка", "Варавино-Фактория"],
    "Калининград": ["Ленинградский", "Московский", "Центральный", "Амалиенау", "Сельма"],
})

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
        con.execute("""
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                first_seen REAL NOT NULL,
                last_seen REAL NOT NULL
            )
        """)
        con.commit()

init_db()

def init_instance_lock_table():
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS instance_lock(
                id INTEGER PRIMARY KEY CHECK(id = 1),
                owner TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        con.commit()

def acquire_instance_lock() -> bool:
    init_instance_lock_table()
    now = time.time()
    ttl = 90
    with db() as con:
        row = con.execute("SELECT owner, updated_at FROM instance_lock WHERE id=1").fetchone()
        if row and row["owner"] != INSTANCE_ID and now - float(row["updated_at"]) < ttl:
            logging.error("Another bot instance is active: %s", row["owner"])
            return False
        con.execute(
            "INSERT OR REPLACE INTO instance_lock(id, owner, updated_at) VALUES(1, ?, ?)",
            (INSTANCE_ID, now),
        )
        con.commit()
    return True

async def instance_heartbeat():
    while True:
        try:
            with db() as con:
                con.execute(
                    "UPDATE instance_lock SET updated_at=? WHERE id=1 AND owner=?",
                    (time.time(), INSTANCE_ID),
                )
                con.commit()
        except Exception as e:
            logging.warning("instance heartbeat failed: %s", e)
        await asyncio.sleep(30)



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

def touch_user(user_id: int | None):
    if not user_id:
        return
    now = time.time()
    try:
        with db() as con:
            con.execute(
                "INSERT INTO users(user_id, first_seen, last_seen) VALUES(?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET last_seen=excluded.last_seen",
                (int(user_id), now, now),
            )
            con.commit()
    except Exception as e:
        logging.warning("touch_user failed: %s", e)

def users_count() -> int:
    try:
        with db() as con:
            row = con.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()
        return int(row["cnt"] if row else 0)
    except Exception:
        return 0

@dp.message.outer_middleware()
async def dedupe_messages(handler, event: types.Message, data: dict):
    touch_user(event.from_user.id if event.from_user else None)
    key = f"m:{event.chat.id}:{event.message_id}"
    if not processed_once(key):
        return
    return await handler(event, data)

@dp.callback_query.outer_middleware()
async def dedupe_callbacks(handler, event: types.CallbackQuery, data: dict):
    touch_user(event.from_user.id if event.from_user else None)
    key = f"c:{event.id}"
    if not processed_once(key):
        try:
            await event.answer()
        except Exception:
            pass
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
    result = []
    for r in rows:
        d = dict(r)
        # Совместимость со старыми значениями группы из прошлых версий.
        if d.get("group_name") in ("основные", "основные товары"):
            d["group_name"] = "main"
        if d.get("group_name") in ("дополнительные", "дополнительные товары"):
            d["group_name"] = "extra"
        result.append(d)
    return result

def group_counts():
    rows = all_products()
    return (
        sum(1 for r in rows if r["group_name"] == "main"),
        sum(1 for r in rows if r["group_name"] == "extra"),
    )

def product_pid(name: str, group: str) -> str:
    import hashlib
    return hashlib.blake2s(f"{group}:{name}".encode("utf-8"), digest_size=4).hexdigest()

def b64s(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")

def unb64s(text: str) -> str:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode((text + pad).encode("ascii")).decode("utf-8")

def compact_product_callback(prefix: str, cc: str, item: dict, district_idx: int | None = None) -> str:
    """
    Самодостаточная callback_data: содержит город, pid, цену и имя товара.
    Это нужно, чтобы кнопка работала даже если другой worker Railway ещё не видит SQLite.
    """
    name64 = b64s(item["name"])
    if district_idx is None:
        cb = f"{prefix}:{cc}:{item['pid']}:{item['price']}:{name64}"
    else:
        cb = f"{prefix}:{cc}:{item['pid']}:{district_idx}:{item['price']}:{name64}"
    # Telegram limit 64 bytes. Если название длинное, fallback на старый короткий формат.
    if len(cb.encode("utf-8")) <= 64:
        return cb
    if district_idx is None:
        return f"prod:{cc}:{item['pid']}"
    return f"dist:{cc}:{item['pid']}:{district_idx}"

def current_catalog(city: str):
    rows = all_products()
    mains_all = [r for r in rows if r["group_name"] == "main"]
    extras_all = [r for r in rows if r["group_name"] == "extra"]

    city_index = ALL_CITIES.index(city) if city in ALL_CITIES else 999
    seed = city + "|" + "|".join(f"{r['group_name']}:{r['name']}:{r['price']}" for r in rows)
    rnd = random.Random(seed)

    if city_index < 50:
        # Первые 50 городов: все основные + рандом 3-6 дополнительных.
        mains = mains_all
        extra_count = rnd.randint(3, 6) if extras_all else 0
    else:
        # Города 51-300: рандом 1-2 основных + рандом 2-4 дополнительных.
        main_count = rnd.randint(1, 2) if mains_all else 0
        mains = rnd.sample(mains_all, min(main_count, len(mains_all))) if mains_all else []
        extra_count = rnd.randint(2, 4) if extras_all else 0

    extras = rnd.sample(extras_all, min(extra_count, len(extras_all))) if extras_all else []

    out = []
    for r in mains + extras:
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


def migrate_json_to_sqlite_once():
    """
    Переносит старые JSON-сохранения в SQLite один раз.
    Это нужно, чтобы товары/кошельки, добавленные в прошлых версиях, не потерялись.
    """
    with db() as con:
        flag = con.execute("SELECT value FROM settings WHERE key='json_migrated'").fetchone()
        if flag:
            return

    paths = []
    for path in ["/data/bot_saved_data.json", "bot_saved_data.json"]:
        if path not in paths and os.path.exists(path):
            paths.append(path)

    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Мигрируем товары только если в SQLite пока пусто.
            if not all_products():
                for idx, (name, price) in enumerate(data.get("products", {}).items(), start=1):
                    with db() as con:
                        con.execute(
                            "INSERT OR REPLACE INTO products(name, price, group_name, sort_order, updated_at) VALUES(?,?,?,?,?)",
                            (str(name), int(price), "main", idx, time.time()),
                        )
                        con.commit()

                offset = len(data.get("products", {}))
                for idx, (name, price) in enumerate(data.get("extra_products", {}).items(), start=1):
                    with db() as con:
                        con.execute(
                            "INSERT OR REPLACE INTO products(name, price, group_name, sort_order, updated_at) VALUES(?,?,?,?,?)",
                            (str(name), int(price), "extra", offset + idx, time.time()),
                        )
                        con.commit()

            # Мигрируем кошельки, если в SQLite по типу пусто.
            wallets = data.get("wallets", {})
            for t in ["btc", "usdt", "ton"]:
                existing = get_wallets(t)
                if not existing:
                    value = wallets.get(t, [])
                    if isinstance(value, str):
                        value = [value] if value.strip() else []
                    for address in value:
                        if str(address).strip():
                            add_wallet(t, str(address).strip())

            about = data.get("about_text")
            if about:
                set_about_text(str(about))
        except Exception as e:
            logging.warning("json migration failed %s: %s", path, e)

    with db() as con:
        con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('json_migrated','1')")
        con.commit()

migrate_json_to_sqlite_once()

def get_districts(city: str, pid: str) -> list[str]:
    city_index = ALL_CITIES.index(city) if city in ALL_CITIES else 999
    if city_index < 50:
        return (LOCATIONS.get(city) or GENERIC_TOP_DISTRICTS)[:5]
    rnd = random.Random(f"{city}:{pid}")
    return rnd.sample(FALLBACK_DISTRICTS, rnd.randint(2, 4))

def item_from_callback_parts(parts: list[str]):
    """
    prodx:<cc>:<pid>:<price>:<name64>
    distx:<cc>:<pid>:<district_idx>:<price>:<name64>
    """
    try:
        if parts[0] == "prodx" and len(parts) == 5:
            _, cc, pid, price_text, name64 = parts
            return cc, {"pid": pid, "name": unb64s(name64), "price": int(price_text), "group": "callback"}, None
        if parts[0] == "distx" and len(parts) == 6:
            _, cc, pid, idx_text, price_text, name64 = parts
            return cc, {"pid": pid, "name": unb64s(name64), "price": int(price_text), "group": "callback"}, int(idx_text)
    except Exception:
        return None, None, None
    return None, None, None

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


def format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days} д")
    if hours:
        parts.append(f"{hours} ч")
    if minutes:
        parts.append(f"{minutes} мин")
    parts.append(f"{seconds} сек")
    return " ".join(parts)

def get_memory_mb() -> float:
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if usage > 10_000_000:
            return usage / 1024 / 1024
        return usage / 1024
    except Exception:
        return 0.0


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
    rows = [
        [InlineKeyboardButton(
            text=f"{x['name']} — {x['price']} ₽",
            callback_data=compact_product_callback("prodx", cc, x),
        )]
        for x in current_catalog(city)
    ]
    rows.append([InlineKeyboardButton(text="🔙 Города", callback_data="city_menu"), InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def districts_keyboard(city: str, item: dict):
    cc = CITY_CODES.get(city, "0")
    districts = get_districts(city, item["pid"])
    rows = [
        [InlineKeyboardButton(
            text=d,
            callback_data=compact_product_callback("distx", cc, item, i),
        )]
        for i, d in enumerate(districts)
    ]
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
        "/cash info — кошельки\n/rates — курсы\n/ping — проверка бота\n/debug — проверка"
    )


@dp.message(F.text.regexp(r"^/ping(@\w+)?(\s|$)"))
async def ping_cmd(m: types.Message):
    try:
        if not await admin_only(m):
            return

        start = time.perf_counter()
        try:
            with db() as con:
                con.execute("SELECT 1").fetchone()
            db_status = "OK"
        except Exception as e:
            db_status = f"ошибка: {escape(str(e))}"

        latency_ms = (time.perf_counter() - start) * 1000
        memory_mb = get_memory_mb()
        uptime = format_uptime(time.time() - BOT_START_TIME)

        await m.answer(
            "🏓 <b>Pong</b>\n\n"
            f"⏱ Время отклика: <b>{latency_ms:.2f} мс</b>\n"
            f"🧠 Memory: <b>{memory_mb:.2f} MB</b>\n"
            f"🕒 Работает: <b>{uptime}</b>\n"
            f"👥 Пользователей: <b>{users_count()}</b>\n"
            f"🗄 SQLite: <b>{db_status}</b>\n"
            f"🆔 Instance: <code>{INSTANCE_ID[:8]}</code>"
        )
    except Exception as e:
        logging.exception("/ping failed")
        try:
            await m.answer(f"❌ Ошибка /ping: <code>{escape(str(e))}</code>")
        except Exception:
            pass

@dp.message(Command("debug"))
async def debug_cmd(m: types.Message):
    if not await admin_only(m): return
    mcnt, ecnt = group_counts()
    await m.answer(
        f"DB: <code>{escape(DB_PATH)}</code>\n"
        f"Основные: <b>{mcnt}</b>\nДополнительные: <b>{ecnt}</b>\n"
        f"BTC/USDT/TON кошельки: <b>{len(get_wallets('btc'))}/{len(get_wallets('usdt'))}/{len(get_wallets('ton'))}</b>\n"
        f"Городов в списке: <b>{len(ALL_CITIES)}</b>"
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
    try:
        if not await admin_only(m): return
        args = command_args(m.text)
        parts = args.split(maxsplit=1)
        if not parts or parts[0].lower() == "info":
            await m.answer(
                f"💳 <b>Кошельки</b>\n\n"
                f"BTC ({len(get_wallets('btc'))}):\n{wallets_text('btc')}\n\n"
                f"USDT ({len(get_wallets('usdt'))}):\n{wallets_text('usdt')}\n\n"
                f"TON ({len(get_wallets('ton'))}):\n{wallets_text('ton')}"
            )
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
            address = parts[1].strip()
            add_wallet(action, address)
            await state.clear()
            await m.answer(
                f"✅ Кошелёк {WALLET_TITLES[action]} добавлен. Всего: <b>{len(get_wallets(action))}</b>\n"
                f"{wallets_text(action)}"
            )
            # Дополнительное короткое сообщение опускает чат вниз после команды.
            await m.answer("⬇️ Сохранено. Можно проверить командой /cash info")
            return
        await state.update_data(cash_type=action)
        await state.set_state(S.cash_wallet)
        await m.answer(f"✍️ Отправьте адрес кошелька {WALLET_TITLES[action]}.")
    except Exception as e:
        logging.exception("/cash failed")
        try:
            await m.answer(f"❌ Ошибка /cash: <code>{escape(str(e))}</code>")
        except Exception:
            pass

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
        await m.answer("❌ Обращение отменено. Повторите команду ещё раз.")
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
    await m.answer(
        f"✅ Кошелёк {WALLET_TITLES[t]} добавлен. Всего: <b>{len(get_wallets(t))}</b>\n"
        f"{wallets_text(t)}"
    )
    await m.answer("⬇️ Сохранено. Можно проверить командой /cash info")

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


@dp.callback_query(F.data.startswith("prodx:"))
async def cb_product_selfcontained(c: types.CallbackQuery, state: FSMContext):
    parts = c.data.split(":")
    cc, item, _ = item_from_callback_parts(parts)
    city = CODE_CITIES.get(cc or "")
    if not city or not item:
        await c.answer("Кнопка устарела.", show_alert=True)
        return

    # Если база видит товар — берём актуальную цену из базы. Если нет — используем данные из callback.
    fresh = resolve_item(city, item["pid"])
    if fresh:
        item = fresh

    await state.update_data(city=city)
    await c.message.answer(
        f"📍 {escape(city)}\n🛍 Товар: <b>{escape(item['name'])}</b> — <b>{item['price']} ₽</b>\n\nВыберите район:",
        reply_markup=districts_keyboard(city, item),
    )

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
        reply_markup=districts_keyboard(city, item),
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
        reply_markup=districts_keyboard(city, item),
    )

@dp.callback_query(F.data.startswith("back:"))
async def cb_back_products(c: types.CallbackQuery, state: FSMContext):
    cc = c.data.split(":", 1)[1]
    city = CODE_CITIES.get(cc) or (await state.get_data()).get("city")
    if city:
        await show_products(c.message, state, city)
    else:
        await show_city_menu(c.message, state)


@dp.callback_query(F.data.startswith("distx:"))
async def cb_dist_selfcontained(c: types.CallbackQuery, state: FSMContext):
    parts = c.data.split(":")
    cc, item, idx = item_from_callback_parts(parts)
    city = CODE_CITIES.get(cc or "")
    if not city or not item or idx is None:
        await c.answer("Кнопка устарела.", show_alert=True)
        return

    fresh = resolve_item(city, item["pid"])
    if fresh:
        item = fresh

    districts = get_districts(city, item["pid"])
    if idx < 0 or idx >= len(districts):
        await c.answer("Район устарел.", show_alert=True)
        return

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
    await c.answer(
        "⛔ По данному заказу оплата ещё не была получена, повторите ваш запрос через 5 минут.",
        show_alert=True,
    )

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
    number = (m.text or "").strip()
    if len(number) == 7:
        await m.answer("⛔ По данному заказу оплата ещё не была получена, повторите ваш запрос через 5 минут.")
    else:
        await m.answer("❌ Ошибка в номере заказа, введите 7 цифр вашего заказа.")


@dp.message(F.text.regexp(r"^/cash(@\w+)?(\s|$)"))
async def cash_cmd_text_fallback(m: types.Message, state: FSMContext):
    await cash_cmd(m, state)

@dp.message(F.text.startswith("/"))
async def unknown(m: types.Message):
    await m.answer("❌ Неизвестная команда. Используйте /help" if is_admin(m.from_user.id if m.from_user else None) else "⛔ Эта команда доступна только администратору бота.")

async def main():
    if not acquire_instance_lock():
        logging.error("Bot stopped: another active instance holds the lock.")
        return

    asyncio.create_task(instance_heartbeat())

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
