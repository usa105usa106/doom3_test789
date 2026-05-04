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

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
BTC_WALLET = os.getenv("BTC_WALLET")
USDT_WALLET = os.getenv("USDT_WALLET")
TON_WALLET = os.getenv("TON_WALLET")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

# ===== FILES =====
FILE_PRODUCTS = "products.json"
FILE_USERS = "users.json"
FILE_ADMIN = "admin.json"
FILE_INFO = "info.txt"

# ===== LOAD =====
import json

def load(path, default):
    try:
        with open(path, "r", encoding="cp1251") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

PRODUCTS = load(FILE_PRODUCTS, {"Футболка": 1200})
USERS = set(load(FILE_USERS, []))
ADMIN_ID = load(FILE_ADMIN, None)
INFO_TEXT = open(FILE_INFO, encoding="cp1251").read() if os.path.exists(FILE_INFO) else "Магазин"

# ===== SAVE =====
def save(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ===== STATES =====
class S(StatesGroup):
    city = State()
    custom_city = State()
    product = State()
    district = State()

# ===== DATA =====
DEFAULT_CITIES = [
    "Москва","Санкт-Петербург","Новосибирск","Екатеринбург","Казань",
    "Нижний Новгород","Челябинск","Омск","Самара","Ростов-на-Дону",
    "Уфа","Красноярск","Воронеж","Пермь","Волгоград"
]

ALL_CITIES = list(dict.fromkeys([
    "Москва","Санкт-Петербург","Новосибирск","Екатеринбург","Казань","Нижний Новгород","Челябинск","Омск","Самара","Ростов-на-Дону",
    "Уфа","Красноярск","Воронеж","Пермь","Волгоград","Краснодар","Саратов","Тюмень","Тольятти","Ижевск","Барнаул","Ульяновск",
    "Иркутск","Хабаровск","Ярославль","Владивосток","Махачкала","Томск","Оренбург","Кемерово","Новокузнецк","Рязань","Астрахань",
    "Набережные Челны","Пенза","Липецк","Тула","Киров","Чебоксары","Курск","Магнитогорск","Сочи","Калининград","Брянск","Иваново",
    "Белгород","Ставрополь","Симферополь","Севастополь","Курган","Архангельск","Сургут","Владимир","Чита","Смоленск","Калуга",
    "Кострома","Грозный","Якутск","Сыктывкар","Мурманск","Тамбов","Химки","Балашиха","Подольск","Королёв","Мытищи","Люберцы",
    "Энгельс","Великий Новгород","Псков","Саранск","Йошкар-Ола","Кызыл","Абакан","Петрозаводск","Северодвинск","Норильск",
    "Ангарск","Благовещенск","Братск","Великие Луки","Волжский","Гатчина","Дзержинск","Димитровград","Евпатория","Жигулёвск",
    "Златоуст","Ивантеевка","Ишим","Ишимбай","Каменск-Уральский","Камышин","Керчь","Кисловодск","Ковров","Коломна",
    "Комсомольск-на-Амуре","Кропоткин","Кстово","Кузнецк","Кыштым","Ленинск-Кузнецкий","Магадан","Междуреченск","Мичуринск","Муром",
    "Находка","Нефтекамск","Нефтеюганск","Нижневартовск","Нижнекамск","Новороссийск","Новотроицк","Новочебоксарск","Новошахтинск","Ногинск",
    "Обнинск","Озёрск","Октябрьский","Орёл","Орск","Павлово","Петропавловск-Камчатский","Прокопьевск","Пятигорск","Рубцовск",
    "Рыбинск","Салават","Северск","Серпухов","Сызрань","Таганрог","Тверь","Тобольск","Торжок","Туапсе",
    "Уссурийск","Ухта","Феодосия","Ханты-Мансийск","Череповец","Черкесск","Шахты","Щёлково","Элиста","Южно-Сахалинск",
    "Азов","Алапаевск","Алексин","Альметьевск","Анапа","Апатиты","Арзамас","Армавир","Артём","Асбест","Ачинск","Балаково",
    "Балахна","Балашов","Белово","Белорецк","Белореченск","Бердск","Березники","Бийск","Бор","Борисоглебск","Боровичи",
    "Будённовск","Бузулук","Великий Устюг","Верхняя Пышма","Видное","Вольск","Воткинск","Выборг","Выкса","Вязьма",
    "Глазов","Губкин","Гуково","Дербент","Дмитров","Дубна","Егорьевск","Ейск","Елец","Ессентуки",
    "Железногорск","Жуковский","Зеленоград","Зерноград","Каменск-Шахтинский","Канск","Каспийск","Кинешма","Кирсанов","Клин",
    "Клинцы","Колпино","Копейск","Котельники","Котлас","Краснотурьинск","Красный Сулин","Крымск","Кунгур","Лабинск",
    "Лесосибирск","Лобня","Лыткарино","Майкоп","Минеральные Воды","Михайловка","Михайловск","Можайск","Мончегорск","Назрань",
    "Нальчик","Нерюнгри","Нефтегорск","Новодвинск","Новозыбков","Новомосковск","Новопавловск","Новочеркасск","Ноябрьск","Нытва",
    "Одинцово","Олекминск","Оленегорск","Онега","Павловский Посад","Партизанск","Петушки","Печора","Плесецк","Покров",
    "Полярные Зори","Приозерск","Прохладный","Пушкин","Пушкино","Раменское","Ревда","Реутов","Ржев","Родники",
    "Россошь","Руза","Ряжск","Салехард","Сафоново","Свободный","Северобайкальск","Североморск","Сегежа","Сергиев Посад",
    "Сердобск","Сертолово","Сестрорецк","Сибай","Славгород","Славянск-на-Кубани","Соликамск","Солнечногорск","Сосновый Бор","Спасск-Дальний",
    "Старица","Старый Оскол","Стерлитамак","Ступино","Тайга","Тайшет","Тара","Татарск","Тейково","Тихвин",
    "Тихорецк","Троицк","Туймазы","Туринск","Тутаев","Тында","Углич","Удачный","Улан-Удэ","Усинск",
    "Усолье-Сибирское","Усть-Илимск","Усть-Лабинск","Фрязино","Фурманов","Хасавюрт","Хотьково","Чайковский","Чапаевск","Черемхово",
    "Черногорск","Чистополь","Шадринск","Шали","Шебекино","Шелехов","Шуя","Электросталь","Юрга","Ялта","Ясногорск"
]))

LOCATIONS = {
    "Москва": ["Тверской","Арбат","Хамовники","Пресненский","Басманный"],
    "Санкт-Петербург": ["Центральный","Адмиралтейский","Петроградский","Выборгский","Василеостровский"],
    "Новосибирск": ["Центральный","Ленинский","Октябрьский","Советский","Калининский"],
    "Екатеринбург": ["Ленинский","Кировский","Чкаловский","Железнодорожный","Октябрьский"],
    "Казань": ["Вахитовский","Советский","Московский","Кировский","Приволжский"],
    "Нижний Новгород": ["Нижегородский","Советский","Автозаводский","Сормовский","Канавинский"],
    "Челябинск": ["Центральный","Калининский","Курчатовский","Советский","Металлургический"],
    "Омск": ["Центральный","Советский","Кировский","Ленинский","Октябрьский"],
    "Самара": ["Ленинский","Октябрьский","Промышленный","Советский","Куйбышевский"],
    "Ростов-на-Дону": ["Ленинский","Кировский","Советский","Ворошиловский","Октябрьский"],
    "Уфа": ["Советский","Кировский","Октябрьский","Ленинский","Калининский"],
    "Красноярск": ["Центральный","Советский","Свердловский","Железнодорожный","Кировский"],
    "Воронеж": ["Центральный","Коминтерновский","Советский","Левобережный","Железнодорожный"],
    "Пермь": ["Ленинский","Свердловский","Индустриальный","Мотовилихинский","Орджоникидзевский"],
    "Волгоград": ["Центральный","Дзержинский","Краснооктябрьский","Ворошиловский","Тракторозаводский"],
    "Краснодар": ["Центральный","Прикубанский","Западный","Карасунский","Фестивальный"],
    "Саратов": ["Волжский","Кировский","Ленинский","Октябрьский","Фрунзенский"],
    "Тюмень": ["Центральный","Ленинский","Калининский","Восточный","Заречный"],
    "Тольятти": ["Автозаводский","Центральный","Комсомольский"],
    "Ижевск": ["Октябрьский","Первомайский","Индустриальный","Устиновский"],
    "Барнаул": ["Центральный","Ленинский","Октябрьский","Железнодорожный"],
    "Ульяновск": ["Ленинский","Засвияжский","Заволжский"],
    "Иркутск": ["Октябрьский","Свердловский","Ленинский"],
    "Хабаровск": ["Центральный","Индустриальный","Краснофлотский"],
    "Ярославль": ["Кировский","Ленинский","Фрунзенский"],
    "Владивосток": ["Ленинский","Первомайский","Фрунзенский"],
    "Махачкала": ["Советский","Ленинский","Кировский"],
    "Томск": ["Ленинский","Октябрьский","Советский"],
    "Оренбург": ["Центральный","Дзержинский","Промышленный"],
    "Кемерово": ["Центральный","Ленинский","Кировский"],
    "Новокузнецк": ["Центральный","Кузнецкий","Заводской"],
    "Рязань": ["Октябрьский","Советский","Московский"],
    "Астрахань": ["Ленинский","Советский","Трусовский"],
    "Набережные Челны": ["Автозаводский","Центральный"],
    "Пенза": ["Ленинский","Октябрьский","Первомайский"],
    "Липецк": ["Советский","Правобережный","Левобережный"],
    "Тула": ["Центральный","Привокзальный","Советский"],
    "Киров": ["Ленинский","Октябрьский","Первомайский"],
    "Чебоксары": ["Ленинский","Калининский","Московский"],
    "Курск": ["Центральный","Сеймский","Железнодорожный"],
    "Магнитогорск": ["Ленинский","Правобережный","Орджоникидзевский"],
    "Сочи": ["Центральный","Адлерский","Хостинский"],
    "Калининград": ["Центральный","Ленинградский","Московский"],
    "Брянск": ["Советский","Бежицкий","Фокинский"],
    "Иваново": ["Ленинский","Октябрьский","Фрунзенский"],
    "Белгород": ["Западный","Восточный","Северный"],
    "Ставрополь": ["Ленинский","Октябрьский","Промышленный"],
    "Симферополь": ["Центральный","Киевский","Железнодорожный"]
}

# ===== KEYBOARDS =====
def main_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="🏙 Выбрать город")],
        [KeyboardButton(text="📦 Мой заказ")],
        [KeyboardButton(text="💰 Проверить оплату")],
        [KeyboardButton(text="ℹ️ О боте")]
    ])

# ===== DISTRICTS =====
def get_districts(city, state_data):
    if "districts" in state_data:
        return state_data["districts"]

    if city in LOCATIONS:
        base = ["Центр"]
        others = random.sample(LOCATIONS[city], min(3, len(LOCATIONS[city])))
        result = base + others
    else:
        pool = ["Автовокзал", "ЖД вокзал", "Любой район"]
        result = ["Центр"] + random.sample(pool, random.randint(1, 3))
    return result

# ===== START =====
@dp.message(Command("start"))
async def start(message: types.Message):
    global ADMIN_ID

    USERS.add(message.from_user.id)
    save(FILE_USERS, list(USERS))

    if ADMIN_ID is None:
        ADMIN_ID = message.from_user.id
        save(FILE_ADMIN, ADMIN_ID)
        await message.answer("👑 Ты админ")

    await message.answer("Добро пожаловать", reply_markup=main_kb())

# ===== CITY =====
@dp.message(lambda m: m.text == "🏙 Выбрать город")
async def city(message: types.Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=c, callback_data=f"city_{c}")] for c in DEFAULT_CITIES
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🌍 Другой город", callback_data="other")])

    await message.answer("Выбери город", reply_markup=kb)

# ===== OTHER =====
@dp.callback_query(lambda c: c.data == "other")
async def other(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введи город")
    await state.set_state(S.custom_city)

@dp.message(S.custom_city)
async def custom_city(message: types.Message, state: FSMContext):
    text = message.text.lower()
    match = [c for c in ALL_CITIES if text in c.lower()]

    if not match:
        return await message.answer("❌ Нет такого города")

    city = match[0]
    await state.update_data(city=city)
    await show_products(message, state)

# ===== SELECT CITY =====
@dp.callback_query(lambda c: c.data.startswith("city_"))
async def select_city(callback: types.CallbackQuery, state: FSMContext):
    city = callback.data.replace("city_", "")
    await state.update_data(city=city)
    await show_products(callback.message, state)

# ===== PRODUCTS =====
async def show_products(message, state):
    data = await state.get_data()

    if "products" not in data:
        prods = list(PRODUCTS.keys()) + random.sample(["Кроссовки","Шарф","Плед"], 2)
        await state.update_data(products=prods)
    else:
        prods = data["products"]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=p, callback_data=f"prod_{p}")] for p in prods
    ])
    await message.answer("Выбери товар", reply_markup=kb)

# ===== PRODUCT =====
@dp.callback_query(lambda c: c.data.startswith("prod_"))
async def product(callback: types.CallbackQuery, state: FSMContext):
    product = callback.data.replace("prod_", "")
    data = await state.get_data()
    city = data["city"]

    districts = get_districts(city, data)
    await state.update_data(districts=districts)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=d, callback_data=f"dist_{d}")] for d in districts
    ])
    await callback.message.edit_text("Выбери район", reply_markup=kb)

# ===== DISTRICT =====
@dp.callback_query(lambda c: c.data.startswith("dist_"))
async def district(callback: types.CallbackQuery, state: FSMContext):
    d = callback.data.replace("dist_", "")
    data = await state.get_data()

    price = random.randint(1000, 3000)
    await callback.message.edit_text(
        f"Заказ создан\n\n"
        f"{data['city']}\n"
        f"{d}\n\n"
        f"{price} ₽\n\n"
        f"⚠️ Кошельки действуют 30 минут"
    )

# ===== RUN =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())