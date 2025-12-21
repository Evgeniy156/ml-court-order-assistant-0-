"""
ML Court Order Assistant - Telegram Bot

Telegram бот с функционалом:
- Регистрация и авторизация
- Просмотр и пополнение баланса
- ML-предсказания
- Просмотр истории транзакций
"""
import os
import sys
import asyncio
import logging
from typing import Optional
from io import BytesIO

# Загрузка переменных окружения из .env файла
try:
    from dotenv import load_dotenv
    # Определяем корень проекта для поиска .env
    _current_file = os.path.abspath(__file__)
    _app_dir = os.path.dirname(os.path.dirname(_current_file))
    _project_root_candidate = os.path.dirname(_app_dir) if os.path.basename(_app_dir) == 'app' else _app_dir
    # Пробуем загрузить .env из корня проекта
    _env_path = os.path.join(_project_root_candidate, '.env')
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
    else:
        # Пробуем загрузить из текущей директории
        load_dotenv()
except ImportError:
    # python-dotenv не установлен, продолжаем без него
    pass

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Добавляем корень проекта в sys.path
# В Docker контейнере: /app/src/telegram_bot.py -> /app
# Локально: app/src/telegram_bot.py -> корень проекта
if '_current_file' not in locals():
    _current_file = os.path.abspath(__file__)
_app_dir = os.path.dirname(os.path.dirname(_current_file))

# Определяем корень проекта (где находится storage)
_storage_in_app = os.path.join(_app_dir, 'storage')
_storage_in_parent = os.path.join(os.path.dirname(_app_dir), 'storage') if _app_dir != '/' else None

if os.path.exists(_storage_in_app):
    _project_root = _app_dir
elif _storage_in_parent and os.path.exists(_storage_in_parent):
    _project_root = os.path.dirname(_app_dir)
elif _app_dir == '/app':
    _project_root = '/app'
else:
    _project_root = os.path.dirname(_app_dir) if os.path.basename(_app_dir) == 'app' else _app_dir

if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from passlib.hash import bcrypt
from storage.db import SessionLocal, engine, Base
from storage.models import UserDB, BillingAccountDB, TransactionDB, MLModelDB
from storage.repository import (
    create_user,
    get_user_by_email,
    deposit_credits,
    withdraw_credits,
    get_user_transactions,
    create_default_ml_models,
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Инициализация бота (отложенная для поддержки импорта без токена)
bot = None
storage = None
dp = None
router = Router()

# Хранение сессий пользователей (telegram_id -> user_id)
user_sessions: dict[int, int] = {}


def init_bot():
    """Инициализация бота с токеном"""
    global bot, storage, dp
    if not BOT_TOKEN or BOT_TOKEN == "your-telegram-bot-token":
        raise ValueError("TELEGRAM_BOT_TOKEN не установлен!")
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    return bot, dp


# ============== FSM States ==============
class AuthStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_password = State()
    waiting_for_register_email = State()
    waiting_for_register_password = State()


class DepositStates(StatesGroup):
    waiting_for_amount = State()


class PredictStates(StatesGroup):
    waiting_for_total_debt = State()
    waiting_for_penalty = State()
    waiting_for_days_overdue = State()
    waiting_for_payments_ratio = State()
    waiting_for_is_physical = State()


class SnilsStates(StatesGroup):
    waiting_for_snils_image = State()


# ============== Клавиатуры ==============
def get_main_keyboard(is_authenticated: bool = False) -> ReplyKeyboardMarkup:
    """Главная клавиатура"""
    if is_authenticated:
        buttons = [
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="➕ Пополнить")],
            [KeyboardButton(text="🔮 Предсказание"), KeyboardButton(text="📜 История")],
            [KeyboardButton(text="🧾 СНИЛС OCR")],
            [KeyboardButton(text="🚪 Выйти")],
        ]
    else:
        buttons = [
            [KeyboardButton(text="🔑 Войти"), KeyboardButton(text="📝 Регистрация")],
        ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_yes_no_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура Да/Нет"""
    buttons = [
        [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


# ============== Хелперы ==============
def get_db():
    """Получить сессию БД"""
    return SessionLocal()


def escape_markdown(text: str) -> str:
    """Экранировать специальные символы Markdown для Telegram"""
    # Экранируем все специальные символы Markdown
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def is_authenticated(telegram_id: int) -> bool:
    """Проверить, авторизован ли пользователь"""
    return telegram_id in user_sessions


def get_current_user_id(telegram_id: int) -> Optional[int]:
    """Получить user_id по telegram_id"""
    return user_sessions.get(telegram_id)


# ============== Команды ==============
@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Команда /start"""
    await state.clear()
    is_auth = is_authenticated(message.from_user.id)
    
    welcome_text = """
🏛️ *ML Court Order Assistant*

Добро пожаловать в систему предсказания пригодности дел для судебного приказа! 

*Возможности:*
• Регистрация и авторизация
• Пополнение баланса кредитов
• ML-предсказания с оплатой кредитами
• Просмотр истории транзакций

Выберите действие:
"""
    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(is_auth),
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Команда /help"""
    help_text = """
📚 *Справка*

*Команды:*
/start - Главное меню
/help - Эта справка
/balance - Проверить баланс
/deposit - Пополнить баланс
/predict - Сделать предсказание
/history - История транзакций
/logout - Выйти из аккаунта

*Как пользоваться:*
1.Зарегистрируйтесь или войдите
2. Пополните баланс
3. Отправляйте данные для предсказания
4. Просматривайте историю операций
"""
    await message.answer(help_text, parse_mode="Markdown")


# ============== Авторизация ==============
@router.message(F.text == "🔑 Войти")
@router.message(Command("login"))
async def start_login(message: types.Message, state: FSMContext):
    """Начать процесс входа"""
    await state.set_state(AuthStates.waiting_for_email)
    await message.answer(
        "Введите ваш email:",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(AuthStates.waiting_for_email)
async def process_login_email(message: types.Message, state: FSMContext):
    """Обработка email при входе"""
    await state.update_data(email=message.text)
    await state.set_state(AuthStates.waiting_for_password)
    await message.answer("Введите пароль:")


@router.message(AuthStates.waiting_for_password)
async def process_login_password(message: types.Message, state: FSMContext):
    """Обработка пароля при входе"""
    data = await state.get_data()
    email = data.get("email")
    password = message.text
    
    db = get_db()
    try:
        user = get_user_by_email(db, email)
        if user and bcrypt.verify(password, user.hashed_password):
            user_sessions[message.from_user.id] = user.id
            await state.clear()
            await message.answer(
                f"✅ Вы успешно вошли как {email}! ",
                reply_markup=get_main_keyboard(True),
            )
        else:
            await state.clear()
            await message.answer(
                "❌ Неверный email или пароль",
                reply_markup=get_main_keyboard(False),
            )
    finally:
        db.close()


# ============== Регистрация ==============
@router.message(F.text == "📝 Регистрация")
@router.message(Command("register"))
async def start_register(message: types.Message, state: FSMContext):
    """Начать процесс регистрации"""
    await state.set_state(AuthStates.waiting_for_register_email)
    await message.answer(
        "Введите email для регистрации:",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(AuthStates.waiting_for_register_email)
async def process_register_email(message: types.Message, state: FSMContext):
    """Обработка email при регистрации"""
    email = message.text
    
    db = get_db()
    try:
        existing = get_user_by_email(db, email)
        if existing:
            await state.clear()
            await message.answer(
                "❌ Этот email уже зарегистрирован",
                reply_markup=get_main_keyboard(False),
            )
            return
    finally:
        db.close()
    
    await state.update_data(email=email)
    await state.set_state(AuthStates.waiting_for_register_password)
    await message.answer("Придумайте пароль (минимум 4 символа):")


@router.message(AuthStates.waiting_for_register_password)
async def process_register_password(message: types.Message, state: FSMContext):
    """Обработка пароля при регистрации"""
    password = message.text
    
    if len(password) < 4:
        await message.answer("❌ Пароль должен быть минимум 4 символа.  Попробуйте ещё раз:")
        return
    
    data = await state.get_data()
    email = data.get("email")
    
    db = get_db()
    try:
        user = create_user(db, email, password)
        user_sessions[message.from_user.id] = user.id
        await state.clear()
        await message.answer(
            f"✅ Регистрация успешна! Добро пожаловать, {email}!",
            reply_markup=get_main_keyboard(True),
        )
    except Exception as e:
        await state.clear()
        await message.answer(
            f"❌ Ошибка регистрации: {e}",
            reply_markup=get_main_keyboard(False),
        )
    finally:
        db.close()


# ============== Выход ==============
@router.message(F.text == "🚪 Выйти")
@router.message(Command("logout"))
async def logout(message: types.Message, state: FSMContext):
    """Выход из аккаунта"""
    await state.clear()
    if message.from_user.id in user_sessions:
        del user_sessions[message.from_user.id]
    await message.answer(
        "👋 Вы вышли из аккаунта",
        reply_markup=get_main_keyboard(False),
    )


# ============== Баланс ==============
@router.message(F.text == "💰 Баланс")
@router.message(Command("balance"))
async def show_balance(message: types.Message):
    """Показать баланс"""
    user_id = get_current_user_id(message.from_user.id)
    if not user_id:
        await message.answer(
            "❌ Сначала войдите в аккаунт",
            reply_markup=get_main_keyboard(False),
        )
        return
    
    db = get_db()
    try:
        account = db.query(BillingAccountDB).filter(
            BillingAccountDB.user_id == user_id
        ).first()
        
        if account:
            await message.answer(
                f"💰 Ваш баланс: *{float(account.balance):.2f}* кредитов",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard(True),
            )
        else:
            await message.answer(
                "❌ Счёт не найден",
                reply_markup=get_main_keyboard(True),
            )
    finally:
        db.close()


# ============== Пополнение ==============
@router.message(F.text == "➕ Пополнить")
@router.message(Command("deposit"))
async def start_deposit(message: types.Message, state: FSMContext):
    """Начать пополнение баланса"""
    user_id = get_current_user_id(message.from_user.id)
    if not user_id:
        await message.answer(
            "❌ Сначала войдите в аккаунт",
            reply_markup=get_main_keyboard(False),
        )
        return
    
    await state.set_state(DepositStates.waiting_for_amount)
    await message.answer(
        "Введите сумму пополнения (в кредитах):",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(DepositStates.waiting_for_amount)
async def process_deposit(message: types.Message, state: FSMContext):
    """Обработка суммы пополнения"""
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")
    except ValueError:
        await message.answer("❌ Введите корректную положительную сумму:")
        return
    
    user_id = get_current_user_id(message.from_user.id)
    
    db = get_db()
    try:
        tx = deposit_credits(
            db,
            user_id=user_id,
            amount=amount,
            description="Пополнение через Telegram бота",
        )
        
        account = db.query(BillingAccountDB).filter(
            BillingAccountDB.user_id == user_id
        ).first()
        
        await state.clear()
        await message.answer(
            f"✅ Баланс пополнен на {amount:.2f} кредитов!\n"
            f"💰 Новый баланс: {float(account.balance):.2f} кредитов",
            reply_markup=get_main_keyboard(True),
        )
    except Exception as e:
        await state.clear()
        await message.answer(
            f"❌ Ошибка пополнения: {e}",
            reply_markup=get_main_keyboard(True),
        )
    finally:
        db.close()


# ============== История ==============
@router.message(F.text == "📜 История")
@router.message(Command("history"))
async def show_history(message: types.Message, state: FSMContext):
    """Показать историю транзакций"""
    # Очищаем состояние FSM, если оно было установлено (чтобы выйти из любого состояния)
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    
    user_id = get_current_user_id(message.from_user.id)
    if not user_id:
        await message.answer(
            "❌ Сначала войдите в аккаунт",
            reply_markup=get_main_keyboard(False),
        )
        return
    
    db = get_db()
    try:
        transactions = get_user_transactions(db, user_id)[:10]  # Последние 10
        
        if not transactions:
            await message.answer(
                "📜 История транзакций пуста",
                reply_markup=get_main_keyboard(True),
            )
            return
        
        history_text = "📜 *Последние транзакции:*\n\n"
        for tx in transactions:
            emoji = "➕" if tx.type == "deposit" else "➖"
            # Экранируем специальные символы Markdown в описании
            description = (tx.description or 'Нет описания').replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]')
            history_text += (
                f"{emoji} {tx.amount:+.2f} кредитов\n"
                f"   📝 {description}\n"
                f"   📅 {tx.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            )
        
        await message.answer(
            history_text,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(True),
        )
    except Exception as e:
        logger.error(f"Ошибка при получении истории транзакций: {e}", exc_info=True)
        await message.answer(
            f"❌ Ошибка при получении истории: {str(e)}",
            reply_markup=get_main_keyboard(True),
        )
    finally:
        db.close()


# ============== Предсказание ==============
@router.message(F.text == "🔮 Предсказание")
@router.message(Command("predict"))
async def start_predict(message: types.Message, state: FSMContext):
    """Начать процесс предсказания"""
    user_id = get_current_user_id(message.from_user.id)
    if not user_id:
        await message.answer(
            "❌ Сначала войдите в аккаунт",
            reply_markup=get_main_keyboard(False),
        )
        return
    
    db = get_db()
    try:
        # Проверяем баланс
        account = db.query(BillingAccountDB).filter(
            BillingAccountDB.user_id == user_id
        ).first()
        
        model = db.query(MLModelDB).filter(
            MLModelDB.name == "court_order_suitability_v1"
        ).first()
        
        if not model:
            await message.answer(
                "❌ ML модель не найдена",
                reply_markup=get_main_keyboard(True),
            )
            return
        
        if not account or float(account.balance) < model.price_credits:
            await message.answer(
                f"❌ Недостаточно кредитов!\n"
                f"Требуется: {model.price_credits}, доступно: {float(account.balance) if account else 0}",
                reply_markup=get_main_keyboard(True),
            )
            return
        
        await state.set_state(PredictStates.waiting_for_total_debt)
        await message.answer(
            f"🔮 *Предсказание пригодности для судебного приказа*\n\n"
            f"Стоимость: {model.price_credits} кредитов\n\n"
            f"Введите *сумму задолженности* (в рублях):",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
    finally:
        db.close()


@router.message(PredictStates.waiting_for_total_debt)
async def process_total_debt(message: types.Message, state: FSMContext):
    """Обработка суммы задолженности"""
    try:
        total_debt = float(message.text)
        if total_debt <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректную положительную сумму:")
        return
    
    await state.update_data(total_debt=total_debt)
    await state.set_state(PredictStates.waiting_for_penalty)
    await message.answer("Введите *сумму пени* (в рублях):", parse_mode="Markdown")


@router.message(PredictStates.waiting_for_penalty)
async def process_penalty(message: types.Message, state: FSMContext):
    """Обработка суммы пени"""
    try:
        penalty = float(message.text)
        if penalty < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректную сумму (0 или больше):")
        return
    
    await state.update_data(penalty_amount=penalty)
    await state.set_state(PredictStates.waiting_for_days_overdue)
    await message.answer("Введите *количество дней просрочки*:", parse_mode="Markdown")


@router.message(PredictStates.waiting_for_days_overdue)
async def process_days_overdue(message: types.Message, state: FSMContext):
    """Обработка дней просрочки"""
    try:
        days = int(message.text)
        if days < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректное число дней (0 или больше):")
        return
    
    await state.update_data(days_overdue=days)
    await state.set_state(PredictStates.waiting_for_payments_ratio)
    await message.answer(
        "Введите *долю оплаченного* (от 0 до 1, например 0.3):",
        parse_mode="Markdown",
    )


@router.message(PredictStates.waiting_for_payments_ratio)
async def process_payments_ratio(message: types.Message, state: FSMContext):
    """Обработка доли оплаченного"""
    try:
        ratio = float(message.text)
        if ratio < 0 or ratio > 1:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите число от 0 до 1:")
        return
    
    await state.update_data(payments_ratio=ratio)
    await state.set_state(PredictStates.waiting_for_is_physical)
    await message.answer(
        "Должник - *физическое лицо*? ",
        parse_mode="Markdown",
        reply_markup=get_yes_no_keyboard(),
    )


@router.message(PredictStates.waiting_for_is_physical)
async def process_is_physical(message: types.Message, state: FSMContext):
    """Обработка типа лица и выполнение предсказания"""
    answer = message.text.lower()
    if answer not in ["да", "нет"]:
        await message.answer("❌ Выберите 'Да' или 'Нет':")
        return
    
    is_physical = answer == "да"
    data = await state.get_data()
    
    user_id = get_current_user_id(message.from_user.id)
    
    db = get_db()
    try:
        # Получаем модель
        model = db.query(MLModelDB).filter(
            MLModelDB.name == "court_order_suitability_v1"
        ).first()
        
        # Проверяем баланс ещё раз
        account = db.query(BillingAccountDB).filter(
            BillingAccountDB.user_id == user_id
        ).first()
        
        if float(account.balance) < model.price_credits:
            await state.clear()
            await message.answer(
                "❌ Недостаточно кредитов",
                reply_markup=get_main_keyboard(True),
            )
            return
        
        # Вычисляем предсказание
        prediction = calculate_prediction(
            total_debt=data["total_debt"],
            penalty_amount=data["penalty_amount"],
            days_overdue=data["days_overdue"],
            payments_ratio=data["payments_ratio"],
            is_physical_person=is_physical,
        )
        
        # Списываем кредиты
        withdraw_credits(
            db,
            user_id=user_id,
            amount=model.price_credits,
            description=f"ML prediction: {model.name}",
        )
        
        # Обновляем баланс
        db.refresh(account)
        
        await state.clear()
        
        # Интерпретация результата
        if prediction >= 0.7:
            verdict = "✅ Высокая вероятность успеха"
        elif prediction >= 0.4:
            verdict = "⚠️ Средняя вероятность успеха"
        else:
            verdict = "❌ Низкая вероятность успеха"
        
        await message.answer(
            f"🔮 *Результат предсказания*\n\n"
            f"*Вероятность успеха:* {prediction:.1%}\n"
            f"*Вердикт:* {verdict}\n\n"
            f"📊 *Входные данные:*\n"
            f"• Сумма долга: {data['total_debt']:.2f} руб.\n"
            f"• Пени: {data['penalty_amount']:.2f} руб.\n"
            f"• Дней просрочки: {data['days_overdue']}\n"
            f"• Доля оплаченного: {data['payments_ratio']:.1%}\n"
            f"• Физ. лицо: {'Да' if is_physical else 'Нет'}\n\n"
            f"💳 Списано: {model.price_credits} кредитов\n"
            f"💰 Остаток: {float(account.balance):.2f} кредитов",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(True),
        )
    except Exception as e:
        await state.clear()
        await message.answer(
            f"❌ Ошибка предсказания: {e}",
            reply_markup=get_main_keyboard(True),
        )
    finally:
        db.close()


def calculate_prediction(
    total_debt: float,
    penalty_amount: float,
    days_overdue: int,
    payments_ratio: float,
    is_physical_person: bool,
) -> float:
    """
    Простая эвристика для расчета вероятности успеха судебного приказа. 
    """
    score = 0.5
    
    # Сумма долга
    if 0 < total_debt <= 100000:
        score += 0.2
    elif total_debt > 100000:
        score -= 0.1
    
    # Просрочка
    if days_overdue > 90:
        score += 0.1
    
    # Физлицо
    if is_physical_person:
        score += 0.05
    
    # Доля оплаченного
    score -= payments_ratio * 0.2
    
    return max(0.0, min(1.0, score))


# ============== СНИЛС OCR ==============
SNILS_API_BASE_URL = os.getenv("SNILS_API_BASE_URL", "http://localhost:8000")


@router.message(F.text == "🧾 СНИЛС OCR")
async def start_snils_ocr(message: types.Message, state: FSMContext):
    """Начать процесс распознавания СНИЛС"""
    if not is_authenticated(message.from_user.id):
        await message.answer(
            "❌ Для использования этой функции необходимо войти в систему.",
            reply_markup=get_main_keyboard(False),
        )
        return
    
    await state.set_state(SnilsStates.waiting_for_snils_image)
    await message.answer(
        "Пришлите фото/скан (JPG/PNG) страницы с полем СНИЛС. Можно лист с несколькими строками.\n\n"
        "Для отмены: /start",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(SnilsStates.waiting_for_snils_image, F.photo)
async def process_snils_photo(message: types.Message, state: FSMContext):
    """Обработка фото для распознавания СНИЛС"""
    try:
        # Скачиваем фото в память (берем самое большое)
        photos = message.photo
        if not photos:
            await message.answer("❌ Не удалось получить фото. Попробуйте ещё раз.")
            return
        
        # Берем самое большое фото
        largest_photo = max(photos, key=lambda p: p.file_size)
        
        # Показываем индикацию загрузки
        await bot.send_chat_action(message.chat.id, "typing")
        
        # Скачиваем файл
        file = await bot.get_file(largest_photo.file_id)
        file_bytes = BytesIO()
        await bot.download_file(file.file_path, destination=file_bytes)
        file_bytes.seek(0)
        image_bytes = file_bytes.read()
        
        # Вызываем API через httpx
        import httpx
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{SNILS_API_BASE_URL}/snils/recognize",
                    files={"file": ("image.jpg", image_bytes, "image/jpeg")},
                )
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            error_msg = (
                "❌ Не удалось подключиться к серверу распознавания.\n\n"
                f"💡 Проверьте:\n"
                f"• Запущен ли FastAPI сервер на {SNILS_API_BASE_URL}\n"
                f"• Правильно ли указан адрес в SNILS_API_BASE_URL\n"
                f"• Доступен ли сервер в сети\n\n"
                f"Для запуска API сервера:\n"
                f"uvicorn app.src.main:app --host 0.0.0.0 --port 8001"
            )
            await message.answer(
                error_msg,
                reply_markup=get_main_keyboard(True),
            )
            await state.clear()
            return
        except httpx.TimeoutException:
            await message.answer(
                "❌ Превышено время ожидания ответа от сервера.\n\n"
                "Попробуйте ещё раз через несколько секунд.",
                reply_markup=get_main_keyboard(True),
            )
            await state.clear()
            return
        
        if response.status_code != 200:
            await message.answer(
                f"❌ Ошибка API: {response.status_code}. Попробуйте ещё раз.",
                reply_markup=get_main_keyboard(True),
            )
            await state.clear()
            return
        
        result = response.json()
        
        # Формируем ответ пользователю
        count = result.get("count", 0)
        
        if count == 0:
            error_msg = "Не нашёл строки СНИЛС.\nСовет: отправьте как Документ (без сжатия) или сделайте фото ближе и резче."
            await message.answer(
                error_msg,
                reply_markup=get_main_keyboard(True),
            )
            await state.clear()
            return
        
        # Выводим копируемые строки СНИЛС (одна строка = один СНИЛС)
        snils_list = []
        for row_result in result.get("results", []):
            snils_formatted = row_result.get('snils_formatted_masked', 'N/A')
            is_valid = row_result.get('is_valid_checksum', False)
            confidence = row_result.get('confidence', 0)
            status_marker = "✅" if is_valid else "⚠️"
            snils_list.append(f"{snils_formatted} {status_marker} {confidence:.0%}")
        
        response_text = "\n".join(snils_list)
        await message.answer(
            response_text,
            reply_markup=get_main_keyboard(True),
        )
        
    except Exception as e:
        logger.error(f"Ошибка при распознавании СНИЛС: {str(e)}")
        await message.answer(
            f"❌ Ошибка при распознавании: {escape_markdown(str(e))}",
            reply_markup=get_main_keyboard(True),
        )
    finally:
        await state.clear()


@router.message(SnilsStates.waiting_for_snils_image, F.document)
async def process_snils_document(message: types.Message, state: FSMContext):
    """Обработка документа для распознавания СНИЛС"""
    try:
        # Проверяем тип документа
        if message.document.mime_type not in ["image/jpeg", "image/jpg", "image/png"]:
            await message.answer(
                "❌ Поддерживаются только JPG и PNG изображения. Попробуйте ещё раз.",
            )
            return
        
        # Показываем индикацию загрузки
        await bot.send_chat_action(message.chat.id, "typing")
        
        # Скачиваем файл
        file = await bot.get_file(message.document.file_id)
        file_bytes = BytesIO()
        await bot.download_file(file.file_path, destination=file_bytes)
        file_bytes.seek(0)
        image_bytes = file_bytes.read()
        
        # Вызываем API через httpx
        import httpx
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{SNILS_API_BASE_URL}/snils/recognize",
                    files={"file": (message.document.file_name or "image.jpg", image_bytes, message.document.mime_type)},
                )
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            error_msg = (
                "❌ Не удалось подключиться к серверу распознавания.\n\n"
                f"💡 Проверьте:\n"
                f"• Запущен ли FastAPI сервер на {SNILS_API_BASE_URL}\n"
                f"• Правильно ли указан адрес в SNILS_API_BASE_URL\n"
                f"• Доступен ли сервер в сети\n\n"
                f"Для запуска API сервера:\n"
                f"uvicorn app.src.main:app --host 0.0.0.0 --port 8001"
            )
            await message.answer(
                error_msg,
                reply_markup=get_main_keyboard(True),
            )
            await state.clear()
            return
        except httpx.TimeoutException:
            await message.answer(
                "❌ Превышено время ожидания ответа от сервера.\n\n"
                "Попробуйте ещё раз через несколько секунд.",
                reply_markup=get_main_keyboard(True),
            )
            await state.clear()
            return
        
        if response.status_code != 200:
            await message.answer(
                f"❌ Ошибка API: {response.status_code}. Попробуйте ещё раз.",
                reply_markup=get_main_keyboard(True),
            )
            await state.clear()
            return
        
        result = response.json()
        
        # Формируем ответ пользователю
        count = result.get("count", 0)
        
        if count == 0:
            error_msg = "Не нашёл строки СНИЛС.\nСовет: отправьте как Документ (без сжатия) или сделайте фото ближе и резче."
            await message.answer(
                error_msg,
                reply_markup=get_main_keyboard(True),
            )
            await state.clear()
            return
        
        # Выводим копируемые строки СНИЛС (одна строка = один СНИЛС)
        snils_list = []
        for row_result in result.get("results", []):
            snils_formatted = row_result.get('snils_formatted_masked', 'N/A')
            is_valid = row_result.get('is_valid_checksum', False)
            confidence = row_result.get('confidence', 0)
            status_marker = "✅" if is_valid else "⚠️"
            snils_list.append(f"{snils_formatted} {status_marker} {confidence:.0%}")
        
        response_text = "\n".join(snils_list)
        await message.answer(
            response_text,
            reply_markup=get_main_keyboard(True),
        )
        
    except Exception as e:
        logger.error(f"Ошибка при распознавании СНИЛС: {str(e)}")
        await message.answer(
            f"❌ Ошибка при распознавании: {escape_markdown(str(e))}",
            reply_markup=get_main_keyboard(True),
        )
    finally:
        await state.clear()


# ============== Обработка неизвестных сообщений ==============
@router.message()
async def unknown_message(message: types.Message):
    """Обработка неизвестных сообщений"""
    is_auth = is_authenticated(message.from_user.id)
    await message.answer(
        "🤔 Не понимаю.  Используйте кнопки меню или команду /help",
        reply_markup=get_main_keyboard(is_auth),
    )


# ============== Запуск бота ==============
async def main():
    """Главная функция запуска бота"""
    # Инициализация бота
    bot, dp = init_bot()
    
    # Инициализация БД
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        create_default_ml_models(db)
    finally:
        db.close()
    
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    if not BOT_TOKEN or BOT_TOKEN == "your-telegram-bot-token":
        print("❌ Установите TELEGRAM_BOT_TOKEN в переменных окружения!")
        print("Получите токен у @BotFather в Telegram")
        sys.exit(1)
    
    asyncio.run(main())
