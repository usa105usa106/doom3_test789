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

# Файл сохранения.
# Для Railway лучше задать переменную DATA_SAVE_FILE=/data/bot_saved_data.json
DATA_SAVE_FILE = os.getenv(
    "DATA_SAVE_FILE",
    "/data/bot_saved_data.json" if os.path.exists("/data") else "bot_saved_data.json"
)

# =====================
# ADMIN CONFIG
# =====================

HARD_ADMIN_IDS: list[int] = [5172121123]  # основной админ

def _load_admin_ids() -> set[int]:
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
    return user_id is not None and int(user_id) in ADMIN_IDS

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
    "Шарф": 900,
}

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

ALL_CITIES = [
    "Москва",
    "Санкт-Петербург",
    "Новосибирск",
    "Екатеринбург",
    "Казань",
    "Нижний Новгород",
    "Челябинск",
    "Омск",
    "Самара",
    "Ростов-на-Дону",
    "Уфа",
    "Красноярск",
    "Воронеж",
    "Пермь",
    "Волгоград",
    "Краснодар",
    "Саратов",
    "Тюмень",
    "Тольятти",
    "Ижевск",
    "Барнаул",
    "Ульяновск",
    "Иркутск",
    "Хабаровск",
    "Ярославль",
    "Владивосток",
    "Махачкала",
    "Томск",
    "Оренбург",
    "Кемерово",
    "Новокузнецк",
    "Рязань",
    "Астрахань",
    "Пенза",
    "Липецк",
    "Киров",
    "Чебоксары",
    "Брянск",
    "Тула",
    "Курск",
    "Ставрополь",
    "Улан-Удэ",
    "Тверь",
    "Магнитогорск",
    "Сочи",
    "Иваново",
    "Белгород",
    "Архангельск",
    "Калининград",
    "Владимир",
    "Смоленск",
    "Калуга",
    "Чита",
    "Грозный",
    "Якутск",
    "Сургут",
    "Нижневартовск",
    "Набережные Челны",
    "Стерлитамак",
    "Орёл",
    "Волжский",
    "Кострома",
    "Петрозаводск",
    "Новороссийск",
    "Йошкар-Ола",
    "Сыктывкар",
    "Нальчик",
    "Абакан",
    "Благовещенск",
    "Дзержинск",
    "Шахты",
    "Энгельс",
    "Балаково",
    "Прокопьевск",
    "Армавир",
    "Псков",
    "Бийск",
    "Рубцовск",
    "Норильск",
    "Северодвинск",
    "Ангарск",
    "Братск",
    "Южно-Сахалинск",
    "Каменск-Уральский",
    "Орск",
    "Златоуст",
    "Элиста",
    "Петропавловск-Камчатский",
    "Нижнекамск",
    "Химки",
    "Королёв",
    "Мытищи",
    "Подольск",
    "Люберцы",
    "Серпухов",
    "Одинцово",
    "Красногорск",
    "Балашиха",
    "Раменское",
    "Жуковский",
    "Мурманск",
    "Вологда",
    "Череповец",
    "Владикавказ",
    "Саранск",
    "Тамбов",
    "Таганрог",
    "Комсомольск-на-Амуре",
    "Старый Оскол",
    "Великий Новгород",
    "Нижний Тагил",
    "Димитровград",
    "Назрань",
    "Хасавюрт",
    "Каспийск",
    "Дербент",
    "Кызыл",
    "Миасс",
    "Находка",
    "Уссурийск",
    "Коломна",
    "Электросталь",
    "Домодедово",
    "Щёлково",
    "Новомосковск",
    "Первоуральск",
    "Березники",
    "Кисловодск",
    "Ессентуки",
    "Пятигорск",
    "Невинномысск",
    "Ковров",
    "Муром",
    "Новочеркасск",
    "Батайск",
    "Каменск-Шахтинский",
    "Азов",
    "Елец",
    "Мичуринск",
    "Обнинск",
    "Северск",
    "Ачинск",
    "Канск",
    "Минусинск",
    "Лесосибирск",
    "Нефтеюганск",
    "Ноябрьск",
    "Новый Уренгой",
    "Муравленко",
    "Губкинский",
    "Салехард",
    "Лабытнанги",
    "Ханты-Мансийск",
    "Когалым",
    "Мегион",
    "Радужный",
    "Лангепас",
    "Пыть-Ях",
    "Ишим",
    "Тобольск",
    "Нефтекамск",
    "Октябрьский",
    "Салават",
    "Ишимбай",
    "Белорецк",
    "Сибай",
    "Кумертау",
    "Мелеуз",
    "Бирск",
    "Туймазы",
    "Бугульма",
    "Альметьевск",
    "Елабуга",
    "Зеленодольск",
    "Бавлы",
    "Лениногорск",
    "Чистополь",
    "Нурлат",
    "Азнакаево",
    "Глазов",
    "Воткинск",
    "Сарапул",
    "Можга",
    "Чайковский",
    "Соликамск",
    "Кунгур",
    "Лысьва",
    "Краснокамск",
    "Губаха",
    "Добрянка",
    "Кудымкар",
    "Серов",
    "Асбест",
    "Полевской",
    "Ревда",
    "Верхняя Пышма",
    "Новоуральск",
    "Краснотурьинск",
    "Лесной",
    "Качканар",
    "Алапаевск",
    "Ирбит",
    "Копейск",
    "Троицк",
    "Озёрск",
    "Снежинск",
    "Сатка",
    "Аша",
    "Коркино",
    "Южноуральск",
    "Еманжелинск",
    "Кыштым",
    "Курган",
    "Шадринск",
    "Далматово",
    "Петухово",
    "Макушино",
    "Бугуруслан",
    "Бузулук",
    "Гай",
    "Новотроицк",
    "Соль-Илецк",
    "Медногорск",
    "Сорочинск",
    "Кувандык",
    "Сызрань",
    "Новокуйбышевск",
    "Чапаевск",
    "Отрадный",
    "Жигулёвск",
    "Кинель",
    "Похвистнево",
    "Бор",
    "Арзамас",
    "Саров",
    "Кстово",
    "Павлово",
    "Выкса",
    "Балахна",
    "Заволжье",
    "Городец",
    "Шуя",
    "Кинешма",
    "Вичуга",
    "Фурманов",
    "Тейково",
    "Родники",
    "Кольчугино",
    "Александров",
    "Гусь-Хрустальный",
    "Вязники",
    "Рыбинск",
    "Переславль-Залесский",
    "Углич",
    "Тутаев",
    "Ростов Великий",
    "Ржев",
    "Вышний Волочёк",
    "Кимры",
    "Торжок",
    "Конаково",
    "Бежецк",
    "Великие Луки",
    "Остров",
    "Печоры",
    "Невель",
    "Старая Русса",
    "Боровичи",
    "Валдай",
    "Кириши",
    "Выборг",
    "Гатчина",
    "Сосновый Бор",
    "Тихвин",
    "Всеволожск",
    "Кингисепп",
    "Луга",
    "Сертолово",
    "Волхов",
    "Тосно",
    "Пушкин",
    "Колпино",
    "Петергоф",
    "Кронштадт",
    "Ломоносов",
    "Котлас",
    "Новодвинск",
    "Коряжма",
    "Мирный",
    "Онега",
    "Вельск",
    "Нарьян-Мар",
    "Апатиты",
    "Североморск",
    "Мончегорск",
    "Кандалакша",
    "Оленегорск",
    "Костомукша",
    "Сортавала",
    "Кондопога",
    "Сегежа",
    "Медвежьегорск",
    "Великий Устюг",
    "Сокол",
    "Шексна",
    "Грязовец",
    "Буй",
    "Шарья",
    "Нерехта",
    "Галич",
    "Мантурово",
    "Клин",
    "Дмитров",
    "Солнечногорск",
    "Ногинск",
    "Пушкино",
    "Орехово-Зуево",
    "Сергиев Посад",
    "Воскресенск",
    "Лобня",
    "Долгопрудный",
    "Реутов",
    "Дубна",
    "Егорьевск",
    "Наро-Фоминск",
    "Чехов",
    "Ступино",
    "Кашира",
    "Видное",
    "Истра",
    "Фрязино",
    "Лыткарино",
    "Дзержинский",
    "Котельники",
    "Луховицы",
    "Можайск",
    "Руза",
    "Зарайск",
    "Волоколамск",
    "Клинцы",
    "Новозыбков",
    "Дятьково",
    "Унеча",
    "Севск",
    "Алексин",
    "Ефремов",
    "Узловая",
    "Щёкино",
    "Донской",
    "Кимовск",
    "Киреевск",
    "Суворов",
    "Мценск",
    "Ливны",
    "Железногорск",
    "Курчатов",
    "Льгов",
    "Рыльск",
    "Губкин",
    "Шебекино",
    "Алексеевка",
    "Валуйки",
    "Строитель",
    "Россошь",
    "Борисоглебск",
    "Лиски",
    "Острогожск",
    "Нововоронеж",
    "Павловск",
    "Семилуки",
    "Моршанск",
    "Рассказово",
    "Котовск",
    "Уварово",
    "Кирсанов",
    "Кузнецк",
    "Заречный",
    "Каменка",
    "Сердобск",
    "Нижний Ломов",
    "Сасово",
    "Скопин",
    "Касимов",
    "Шацк",
    "Вязьма",
    "Рославль",
    "Сафоново",
    "Ярцево",
    "Гагарин",
    "Десногорск",
    "Людиново",
    "Киров Калужский",
    "Малоярославец",
    "Балабаново",
    "Козельск",
    "Кондрово",
    "Ейск",
    "Кропоткин",
    "Анапа",
    "Геленджик",
    "Туапсе",
    "Тихорецк",
    "Славянск-на-Кубани",
    "Белореченск",
    "Лабинск",
    "Апшеронск",
    "Горячий Ключ",
    "Крымск",
    "Темрюк",
    "Кореновск",
    "Усть-Лабинск",
    "Майкоп",
    "Адыгейск",
    "Черкесск",
    "Карачаевск",
    "Будённовск",
    "Георгиевск",
    "Минеральные Воды",
    "Михайловск",
    "Изобильный",
    "Светлоград",
    "Зеленокумск",
    "Лермонтов",
    "Баксан",
    "Прохладный",
    "Моздок",
    "Беслан",
    "Малгобек",
    "Аргун",
    "Гудермес",
    "Шали",
    "Урус-Мартан",
    "Кизляр",
    "Буйнакск",
    "Избербаш",
    "Кизилюрт",
    "Дагестанские Огни",
    "Южно-Сухокумск",
    "Волгодонск",
    "Гуково",
    "Донецк",
    "Зверево",
    "Миллерово",
    "Морозовск",
    "Сальск",
    "Семикаракорск",
    "Цимлянск",
    "Фролово",
    "Камышин",
    "Михайловка",
    "Урюпинск",
    "Котельниково",
    "Калач-на-Дону",
    "Палласовка",
    "Дубовка",
    "Ахтубинск",
    "Знаменск",
    "Харабали",
    "Камызяк",
    "Нариманов",
    "Вольск",
    "Балашов",
    "Маркс",
    "Пугачёв",
    "Ртищево",
    "Аткарск",
    "Петровск",
    "Хвалынск",
    "Ершов",
    "Новоузенск",
    "Красноармейск",
]
CITY_CODES = {city: str(i) for i, city in enumerate(ALL_CITIES)}
CODE_CITIES = {str(i): city for i, city in enumerate(ALL_CITIES)}

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
    "Симферополь": ["Центральный", "Киевский", "Железнодорожный"],
}

TOP_CITIES = set(ALL_CITIES[:50])
FALLBACK_DISTRICTS = ["Центр", "Автовокзал", "ЖД/вокзал", "Любой район", "Ленинский", "Советский", "Октябрьский", "Центральный"]
GENERIC_TOP_DISTRICTS = ["Центр", "Ленинский", "Советский", "Октябрьский", "Центральный"]

WALLETS = {
    "btc": [],
    "usdt": [],
    "ton": [],
}
WALLET_TITLES = {
    "btc": "BTC",
    "usdt": "USDT-(TRC20)",
    "ton": "TON",
}

BTC_RATE = float(os.getenv("BTC_RATE", "9500000"))
USDT_TRC20_RATE = float(os.getenv("USDT_TRC20_RATE", "90"))
TON_RATE = float(os.getenv("TON_RATE", "270"))
_rates_cache = {"ts": 0, "rates": None}

ABOUT_TEXT = "🛒 Это автоматический маркетплейс.\nОплата только в криптовалюте.\nКошельки действительны 30 минут."

# =====================
# HELPERS
# =====================

def normalize_wallets() -> None:
    for key, value in list(WALLETS.items()):
        if isinstance(value, str):
            WALLETS[key] = [value] if value.strip() else []
        else:
            WALLETS[key] = [str(x).strip() for x in value if str(x).strip()]

def save_bot_data() -> None:
    normalize_wallets()
    data = {
        "products": PRODUCTS,
        "extra_products": EXTRA_PRODUCTS,
        "wallets": WALLETS,
        "about_text": ABOUT_TEXT,
    }
    parent = os.path.dirname(DATA_SAVE_FILE)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(DATA_SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_bot_data() -> bool:
    global ABOUT_TEXT
    if not os.path.exists(DATA_SAVE_FILE):
        return False

    with open(DATA_SAVE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    PRODUCTS.clear()
    PRODUCTS.update({str(k): int(v) for k, v in data.get("products", {}).items()})

    EXTRA_PRODUCTS.clear()
    EXTRA_PRODUCTS.update({str(k): int(v) for k, v in data.get("extra_products", {}).items()})

    saved_wallets = data.get("wallets", {})
    for key in WALLETS:
        value = saved_wallets.get(key, [])
        if isinstance(value, str):
            value = [value] if value.strip() else []
        WALLETS[key] = [str(x).strip() for x in value if str(x).strip()]

    ABOUT_TEXT = str(data.get("about_text", ABOUT_TEXT))
    return True

def city_products(city: str) -> dict:
    result = dict(PRODUCTS)
    if EXTRA_PRODUCTS:
        rnd = random.Random(city)
        count = min(rnd.randint(3, 6), len(EXTRA_PRODUCTS))
        extra_names = rnd.sample(list(EXTRA_PRODUCTS.keys()), count)
        for name in extra_names:
            result[name] = EXTRA_PRODUCTS[name]
    return result

def get_city_districts(city: str) -> list[str]:
    if city in TOP_CITIES:
        return (LOCATIONS.get(city) or GENERIC_TOP_DISTRICTS)[:5]
    # Для городов после 50 по популярности: случайные 2-4 района.
    # Набор стабилен для одного города, чтобы кнопки не менялись во время заказа.
    rnd = random.Random(f"districts:{city}")
    count = rnd.randint(2, 4)
    return rnd.sample(FALLBACK_DISTRICTS, count)

def city_code(city: str) -> str:
    return CITY_CODES.get(city, "x")

def city_from_code(code: str, data: dict | None = None) -> str | None:
    if code in CODE_CITIES:
        return CODE_CITIES[code]
    if data:
        return data.get("city")
    return None

def get_random_wallet(wallet_type: str) -> str:
    normalize_wallets()
    wallets = WALLETS.get(wallet_type, [])
    return random.choice(wallets) if wallets else "не задан"

def wallets_text(wallet_type: str) -> str:
    normalize_wallets()
    wallets = WALLETS.get(wallet_type, [])
    if not wallets:
        return "не задан"
    return "\n".join(f"• <code>{escape(w)}</code>" for w in wallets)

def products_info_text() -> str:
    lines = ["📦 <b>Весь товар с ценами</b>\n"]
    if PRODUCTS:
        lines.append("<b>Основные товары:</b>")
        lines.extend(f"• {escape(name)} — <b>{price} ₽</b>" for name, price in PRODUCTS.items())
    else:
        lines.append("<b>Основные товары:</b>\nнет товаров")

    lines.append("")
    if EXTRA_PRODUCTS:
        lines.append("<b>Дополнительные товары:</b>")
        lines.extend(f"• {escape(name)} — <b>{price} ₽</b>" for name, price in EXTRA_PRODUCTS.items())
    else:
        lines.append("<b>Дополнительные товары:</b>\nнет товаров")
    return "\n".join(lines)

def fmt_amount(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}".rstrip("0").rstrip(".")

def get_live_rates() -> dict:
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
    return (
        fmt_amount(rub / rates["btc"], 8),
        fmt_amount(rub / rates["usdt"], 2),
        fmt_amount(rub / rates["ton"], 3),
    )

def command_args(text: str) -> str:
    parts = (text or "").split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""

def find_supported_city(raw_city: str) -> str | None:
    """Проверяет город по списку поддерживаемых городов."""
    normalized = " ".join((raw_city or "").strip().split()).lower()
    if not normalized:
        return None
    for city in ALL_CITIES:
        if city.lower() == normalized:
            return city
    return None

def main_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="🏙 Выбрать город")],
        [KeyboardButton(text="📦 Мой заказ")],
        [KeyboardButton(text="💰 Проверить оплату")],
        [KeyboardButton(text="ℹ️ О боте")],
    ])

def city_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=x, callback_data=f"c:{CITY_CODES[x]}")]
        for x in ALL_CITIES[:15]
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔎 Другой город", callback_data="other_city")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])
    return kb

def products_keyboard(city: str):
    products = city_products(city)
    cc = city_code(city)
    rows = []
    for i, (p, price) in enumerate(products.items()):
        rows.append([InlineKeyboardButton(text=f"{p} — {price} ₽", callback_data=f"p:{cc}:{i}")])
    rows.append([
        InlineKeyboardButton(text="🔙 Города", callback_data="city"),
        InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def districts_keyboard(city: str, product_index: int):
    districts = get_city_districts(city)
    cc = city_code(city)
    rows = [
        [InlineKeyboardButton(text=d, callback_data=f"d:{cc}:{product_index}:{i}")]
        for i, d in enumerate(districts)
    ]
    rows.append([
        InlineKeyboardButton(text="🔙 Товары", callback_data="back_products"),
        InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def safe_edit(message: types.Message, text: str, reply_markup=None):
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except Exception:
        await message.answer(text, reply_markup=reply_markup)

try:
    load_bot_data()
except Exception as e:
    logging.warning("Could not auto-load saved bot data: %s", e)

# =====================
# START / MENU
# =====================

@dp.message(F.text.regexp(r"^/start(@\w+)?$"))
async def start(m: types.Message, state: FSMContext):
    if m.from_user:
        uid = int(m.from_user.id)

        # Если пользователь указан в HARD_ADMIN_IDS, гарантированно добавляем его в админы.
        if uid in {int(x) for x in HARD_ADMIN_IDS} and uid not in ADMIN_IDS:
            ADMIN_IDS.add(uid)
            _save_admin_ids()
            logging.info("Hard admin restored: %s", uid)

        # Если админы вообще не заданы, первый пользователь /start становится админом.
        if not ADMIN_IDS:
            ADMIN_IDS.add(uid)
            _save_admin_ids()
            logging.info("Auto admin created: %s", uid)
            await m.answer(
                "✅ Админ не был задан, поэтому вы назначены администратором.\n"
                f"Ваш Telegram ID: <code>{uid}</code>"
            )

    await state.clear()
    await m.answer("🏪 Добро пожаловать в Маркетплейс", reply_markup=main_kb())

@dp.message(F.text == "🏙 Выбрать город")
async def choose_city_btn(m: types.Message, state: FSMContext):
    await state.set_state(S.city)
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

# =====================
# ADMIN COMMANDS
# =====================

@dp.message(F.text.regexp(r"^/adminid(@\w+)?$"))
async def admin_id_cmd(m: types.Message):
    user_id = m.from_user.id if m.from_user else None
    status = "✅ вы админ" if is_admin(user_id) else "⛔ вы не админ"
    await m.answer(f"Ваш Telegram ID: <code>{user_id}</code>\nСтатус: {status}")

@dp.message(F.text.regexp(r"^/help(@\w+)?$"))
async def help_cmd(m: types.Message):
    if not await admin_only(m):
        return
    await m.answer(
        "📋 <b>Список команд</b>\n\n"
        "/start — открыть главное меню\n"
        "/help — список команд администратора\n"
        "/adminid — показать ваш Telegram ID и статус админа\n"
        "/add товар цена — добавить товар, пример: <code>/add книга 500</code>\n"
        "/add info — показать весь товар с ценами\n"
        "/del товар — удалить товар, пример: <code>/del книга</code>\n"
        "/del all — удалить весь товар\n"
        "/info текст — изменить сообщение кнопки «О боте»\n"
        "/cash info — показать все кошельки\n"
        "/cash btc адрес — добавить BTC кошелёк\n"
        "/cash usdt адрес — добавить USDT-(TRC20) кошелёк\n"
        "/cash ton адрес — добавить TON кошелёк\n"
        "/cash del btc|usdt|ton — удалить все кошельки выбранного типа\n"
        "/cash del all — удалить все кошельки\n"
        "/save — сохранить все текущие изменения\n"
        "/load — загрузить последние сохранённые значения\n"
        "Поддерживается ручной ввод города только из списка 300+ городов"
    )

@dp.message(F.text.regexp(r"^/save(@\w+)?$"))
async def save_cmd(m: types.Message):
    if not await admin_only(m):
        return
    try:
        save_bot_data()
        await m.answer(f"✅ Все изменения сохранены.\nФайл: <code>{escape(DATA_SAVE_FILE)}</code>")
    except Exception as e:
        logging.exception("Save failed")
        await m.answer(f"❌ Не удалось сохранить данные: <code>{escape(str(e))}</code>")

@dp.message(F.text.regexp(r"^/load(@\w+)?$"))
async def load_cmd(m: types.Message):
    if not await admin_only(m):
        return
    try:
        if not load_bot_data():
            await m.answer("❌ Сохранение не найдено. Сначала используйте /save.")
            return
        await m.answer("✅ Последние сохранённые значения загружены.")
    except Exception as e:
        logging.exception("Load failed")
        await m.answer(f"❌ Не удалось загрузить данные: <code>{escape(str(e))}</code>")

@dp.message(F.text.regexp(r"^/add(@\w+)?(\s|$)"))
async def add_product_cmd(m: types.Message):
    if not await admin_only(m):
        return

    rest = command_args(m.text)
    if rest.lower() == "info":
        await m.answer(products_info_text())
        return

    if not rest or len(rest.split()) < 2:
        await m.answer("❌ Неверный формат. Пример: <code>/add книга 500</code>\nСписок товаров: <code>/add info</code>")
        return

    name, price_text = rest.rsplit(maxsplit=1)
    if not price_text.isdigit() or int(price_text) <= 0:
        await m.answer("❌ Цена должна быть положительным числом. Пример: <code>/add книга 500</code>")
        return

    product_name = name.strip().capitalize()
    PRODUCTS[product_name] = int(price_text)
    save_bot_data()
    await m.answer(f"✅ Товар добавлен: <b>{escape(product_name)}</b> — <b>{int(price_text)} ₽</b>")

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
        save_bot_data()
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
        save_bot_data()
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
    save_bot_data()
    await m.answer("✅ Сообщение кнопки «О боте» изменено.")

@dp.message(F.text.regexp(r"^/cash(@\w+)?(\s|$)"))
async def cash_cmd(m: types.Message, state: FSMContext):
    if not await admin_only(m):
        return

    args = command_args(m.text)
    parts = args.split(maxsplit=2)

    if not parts or parts[0].lower() == "info":
        await m.answer(
            "💳 <b>Кошельки</b>\n\n"
            f"BTC:\n{wallets_text('btc')}\n\n"
            f"USDT-(TRC20):\n{wallets_text('usdt')}\n\n"
            f"TON:\n{wallets_text('ton')}\n\n"
            "В оплате бот выбирает случайный кошелёк из сохранённых."
        )
        return

    action = parts[0].lower()

    if action == "del":
        if len(parts) < 2:
            await m.answer("❌ Укажите, какой кошелёк удалить: <code>/cash del btc</code>, <code>/cash del usdt</code>, <code>/cash del ton</code> или <code>/cash del all</code>")
            return
        target = parts[1].lower()
        if target == "all":
            for key in WALLETS:
                WALLETS[key] = []
            save_bot_data()
            await m.answer("✅ Все кошельки удалены.")
            return
        if target not in WALLETS:
            await m.answer("❌ Можно удалить только: btc, usdt, ton или all.")
            return
        WALLETS[target] = []
        save_bot_data()
        await m.answer(f"✅ Все кошельки {WALLET_TITLES[target]} удалены.")
        return

    if action not in WALLETS:
        await m.answer("❌ Неверная команда. Используйте: <code>/cash info</code>, <code>/cash btc адрес</code>, <code>/cash usdt адрес</code>, <code>/cash ton адрес</code>, <code>/cash del ...</code>")
        return

    if len(parts) >= 2:
        wallet = " ".join(parts[1:]).strip()
        if not wallet:
            await m.answer("❌ Кошелёк не может быть пустым.")
            return
        normalize_wallets()
        WALLETS[action].append(wallet)
        save_bot_data()
        await state.clear()
        await m.answer(f"✅ Кошелёк {WALLET_TITLES[action]} добавлен: <code>{escape(wallet)}</code>")
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
    wallet = (m.text or "").strip()
    if not wallet:
        await m.answer("❌ Кошелёк не может быть пустым.")
        return
    normalize_wallets()
    WALLETS[cash_type].append(wallet)
    save_bot_data()
    await state.clear()
    await m.answer(f"✅ Кошелёк {WALLET_TITLES[cash_type]} добавлен: <code>{escape(wallet)}</code>")

# =====================
# INLINE HANDLERS
# =====================

@dp.callback_query(F.data == "menu")
async def menu(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await state.clear()
    await safe_edit(c.message, "🏪 Главное меню", reply_markup=None)
    await c.message.answer("Выберите действие:", reply_markup=main_kb())

@dp.callback_query(F.data == "city")
async def back_to_cities(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await state.set_state(S.city)
    await safe_edit(c.message, "🏙 Выберите город:", reply_markup=city_keyboard())

@dp.callback_query(F.data == "other_city")
async def other_city(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await state.set_state(S.city_name)
    await safe_edit(c.message, "✍️ Напишите название города в чат.")

@dp.message(S.city_name)
async def city_name_from_chat(m: types.Message, state: FSMContext):
    city = find_supported_city(m.text or "")
    if not city:
        await m.answer("❌ Нет такого города. Проверьте название и попробуйте ещё раз.")
        return

    await state.update_data(city=city)
    await state.set_state(S.product)
    await m.answer(f"📍 Город: <b>{escape(city)}</b>\n\n🛍 Выберите товар:", reply_markup=products_keyboard(city))

@dp.callback_query(F.data.startswith("c:"))
async def city_selected(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    code = c.data.split(":", 1)[1]
    city = city_from_code(code)
    if not city:
        await safe_edit(c.message, "🏙 Выберите город:", reply_markup=city_keyboard())
        return

    await state.update_data(city=city)
    await state.set_state(S.product)
    await safe_edit(c.message, f"📍 Город: <b>{escape(city)}</b>\n\n🛍 Выберите товар:", reply_markup=products_keyboard(city))

@dp.callback_query(F.data.startswith("p:"))
async def product_selected(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    data = await state.get_data()

    try:
        _, cc, product_index_text = c.data.split(":", 2)
        product_index = int(product_index_text)
    except Exception:
        await c.answer("Кнопка устарела. Выберите город заново.", show_alert=True)
        await state.set_state(S.city)
        await safe_edit(c.message, "🏙 Выберите город:", reply_markup=city_keyboard())
        return

    city = city_from_code(cc, data)
    if not city:
        await c.answer("Сначала выберите город", show_alert=True)
        await state.set_state(S.city)
        await safe_edit(c.message, "🏙 Выберите город:", reply_markup=city_keyboard())
        return

    products = city_products(city)
    product_items = list(products.items())
    if product_index < 0 or product_index >= len(product_items):
        await c.answer("Товар устарел. Выберите товар заново.", show_alert=True)
        await safe_edit(c.message, f"📍 Город: <b>{escape(city)}</b>\n\n🛍 Выберите товар:", reply_markup=products_keyboard(city))
        return

    product, price = product_items[product_index]
    districts = get_city_districts(city)

    await state.update_data(
        city=city,
        product=product,
        product_index=product_index,
        price=price,
        districts=districts,
    )
    await state.set_state(S.district)

    await safe_edit(
        c.message,
        f"📍 {escape(city)}\n🛍 Товар: <b>{escape(product)}</b>\n\nВыберите район:",
        reply_markup=districts_keyboard(city, product_index),
    )

@dp.callback_query(F.data == "back_products")
async def back_products(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    data = await state.get_data()
    city = data.get("city")
    if not city:
        await state.set_state(S.city)
        await safe_edit(c.message, "🏙 Сначала выберите город:", reply_markup=city_keyboard())
        return
    await state.set_state(S.product)
    await safe_edit(c.message, f"📍 Город: <b>{escape(city)}</b>\n\n🛍 Выберите товар:", reply_markup=products_keyboard(city))

@dp.callback_query(F.data.startswith("d:"))
async def district_selected(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    data = await state.get_data()

    try:
        _, cc, product_index_text, district_index_text = c.data.split(":", 3)
        product_index = int(product_index_text)
        district_index = int(district_index_text)
    except Exception:
        await c.answer("Кнопка устарела. Выберите город заново.", show_alert=True)
        await state.set_state(S.city)
        await safe_edit(c.message, "🏙 Выберите город:", reply_markup=city_keyboard())
        return

    city = city_from_code(cc, data)
    if not city:
        await c.answer("Сначала выберите город", show_alert=True)
        await state.set_state(S.city)
        await safe_edit(c.message, "🏙 Выберите город:", reply_markup=city_keyboard())
        return

    products = city_products(city)
    product_items = list(products.items())
    districts = get_city_districts(city)

    if product_index < 0 or product_index >= len(product_items):
        await c.answer("Товар устарел. Выберите товар заново.", show_alert=True)
        await safe_edit(c.message, f"📍 Город: <b>{escape(city)}</b>\n\n🛍 Выберите товар:", reply_markup=products_keyboard(city))
        return

    if district_index < 0 or district_index >= len(districts):
        await c.answer("Район устарел. Выберите район заново.", show_alert=True)
        product, _ = product_items[product_index]
        await safe_edit(
            c.message,
            f"📍 {escape(city)}\n🛍 Товар: <b>{escape(product)}</b>\n\nВыберите район:",
            reply_markup=districts_keyboard(city, product_index),
        )
        return

    product, price = product_items[product_index]
    district = districts[district_index]
    order_id = random.randint(1000000, 9999999)
    await state.update_data(
        city=city,
        product=product,
        product_index=product_index,
        price=price,
        district=district,
        order_id=order_id,
        t=time.time(),
    )

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
        "⏰ Внимание!!! Для покупки товара, оплатите точную сумму на любой из этих кошельков. "
        "Бот находит оплату автоматически после первого подтверждения транзакции в сети. "
        "В целях идентификации платежа - кошельки и сумма актуальны 30 минут. "
        "Если у вас нет криптовалюты, её можно купить за рубли через обменник bestchange.biz, "
        "для создания кошельков используйте trust wallet, скачать можно через google play/app store."
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
async def check_payment(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if time.time() - data.get("t", 0) > 1800:
        await c.answer("⛔ Время на оплату вышло (30 минут)", show_alert=True)
        return
    await c.answer("⛔ По данному заказу оплата не была получена, сначала оплатите и повторите запрос.", show_alert=True)

# =====================
# OTHER MESSAGES
# =====================

@dp.message(F.text.regexp(r"^\d+$"))
async def order_number_from_chat(m: types.Message):
    digits = m.text.strip()
    if len(digits) == 7:
        await m.answer("⛔ По данному заказу оплата не была получена, сначала оплатите и повторите запрос.")
    elif 1 <= len(digits) <= 6 or 8 <= len(digits) <= 20:
        await m.answer("❌ Неверный ввод, убедитесь, что вы вводите 7 цифр вашего заказа.")

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
