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

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm. context import FSMContext
from aiogram.fsm. state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Добавляем корень проекта в sys.path
sys. path.insert(0, os. path.dirname(os.path.dirname(os.path.dirname(os.path. abspath(__file__)))))

from passlib.hash import bcrypt
from storage.db import SessionLocal, engine, Base
from storage.models import UserDB, BillingAccountDB, TransactionDB, MLModelDB, MLTaskDB
from storage.repository import (
    create_user,
    get_user_by_email,
    deposit_credits,
    withdraw_credits,
    get_user_transactions,
    create_default_ml_models,
)

# Импортируем publisher для RabbitMQ
try:
    from .rabbitmq_client import get_publisher
    RABBITMQ_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"RabbitMQ модуль недоступен: {e}")
    RABBITMQ_AVAILABLE = False

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging. getLogger(__name__)

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


# ============== Клавиатуры ==============
def get_main_keyboard(is_authenticated: bool = False) -> ReplyKeyboardMarkup:
    """Главная клавиатура"""
    if is_authenticated:
        buttons = [
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="➕ Пополнить")],
            [KeyboardButton(text="🔮 Предсказание"), KeyboardButton(text="📜 История")],
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


@router. message(Command("help"))
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
    await state.update_data(email=message. text)
    await state.set_state(AuthStates.waiting_for_password)
    await message. answer("Введите пароль:")


@router.message(AuthStates. waiting_for_password)
async def process_login_password(message: types.Message, state: FSMContext):
    """Обработка пароля при входе"""
    data = await state.get_data()
    email = data.get("email")
    password = message.text
    
    db = get_db()
    try:
        user = get_user_by_email(db, email)
        if user and bcrypt.verify(password, user. hashed_password):
            user_sessions[message.from_user. id] = user. id
            await state. clear()
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
        db. close()


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


@router. message(AuthStates.waiting_for_register_email)
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
        db. close()
    
    await state.update_data(email=email)
    await state. set_state(AuthStates.waiting_for_register_password)
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
async def logout(message: types. Message, state: FSMContext):
    """Выход из аккаунта"""
    await state.clear()
    if message.from_user.id in user_sessions:
        del user_sessions[message.from_user. id]
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
@router. message(F.text == "➕ Пополнить")
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
    
    await state.set_state(DepositStates. waiting_for_amount)
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
    
    user_id = get_current_user_id(message.from_user. id)
    
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
            f"✅ Баланс пополнен на {amount:. 2f} кредитов!\n"
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
@router. message(F.text == "📜 История")
@router.message(Command("history"))
async def show_history(message: types.Message):
    """Показать историю транзакций"""
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
            emoji = "➕" if tx. type == "deposit" else "➖"
            history_text += (
                f"{emoji} {tx.amount:+.2f} кредитов\n"
                f"   📝 {tx.description or 'Нет описания'}\n"
                f"   📅 {tx. created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            )
        
        await message.answer(
            history_text,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(True),
        )
    finally:
        db.close()


# ============== Предсказание ==============
@router.message(F. text == "🔮 Предсказание")
@router.message(Command("predict"))
async def start_predict(message: types. Message, state: FSMContext):
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
            MLModelDB. name == "court_order_suitability_v1"
        ).first()
        
        if not model:
            await message. answer(
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
        await message. answer(
            f"🔮 *Предсказание пригодности для судебного приказа*\n\n"
            f"Стоимость: {model.price_credits} кредитов\n\n"
            f"Введите *сумму задолженности* (в рублях):",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
    finally:
        db. close()


@router.message(PredictStates.waiting_for_total_debt)
async def process_total_debt(message: types.Message, state: FSMContext):
    """Обработка суммы задолженности"""
    try:
        total_debt = float(message.text)
        if total_debt <= 0:
            raise ValueError()
    except ValueError:
        await message. answer("❌ Введите корректную положительную сумму:")
        return
    
    await state.update_data(total_debt=total_debt)
    await state.set_state(PredictStates.waiting_for_penalty)
    await message. answer("Введите *сумму пени* (в рублях):", parse_mode="Markdown")


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


@router.message(PredictStates. waiting_for_days_overdue)
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
        await message. answer("❌ Введите число от 0 до 1:")
        return
    
    await state.update_data(payments_ratio=ratio)
    await state.set_state(PredictStates.waiting_for_is_physical)
    await message. answer(
        "Должник - *физическое лицо*? ",
        parse_mode="Markdown",
        reply_markup=get_yes_no_keyboard(),
    )


@router.message(PredictStates. waiting_for_is_physical)
async def process_is_physical(message: types.Message, state: FSMContext):
    """Обработка типа лица и отправка задачи в очередь"""
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
        
        if not model:
            await state.clear()
            await message.answer(
                "❌ ML модель не найдена",
                reply_markup=get_main_keyboard(True),
            )
            return
        
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
        
        # Списываем кредиты сразу
        withdraw_credits(
            db,
            user_id=user_id,
            amount=model.price_credits,
            description=f"ML задача: {model.name}",
        )
        
        # Создаем задачу в БД
        task = MLTaskDB(
            user_id=user_id,
            model_id=model.id,
            status="pending",
            input_data={
                "total_debt": float(data["total_debt"]),
                "penalty_amount": float(data["penalty_amount"]),
                "days_overdue": int(data["days_overdue"]),
                "payments_ratio": float(data["payments_ratio"]),
                "is_physical_person": is_physical,
            },
            credits_charged=model.price_credits,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # Отправляем задачу в RabbitMQ
        if RABBITMQ_AVAILABLE:
            try:
                publisher = get_publisher()
                publisher.publish_task(
                    task_id=task.id,
                    task_data={
                        "user_id": user_id,
                        "model_id": model.id,
                        "input_data": task.input_data,
                    }
                )
                
                await state.clear()
                await message.answer(
                    f"✅ *Задача отправлена на обработку!*\n\n"
                    f"📋 ID задачи: `{task.id}`\n"
                    f"💳 Списано: {model.price_credits} кредитов\n\n"
                    f"⏳ Задача будет обработана воркерами.\n"
                    f"Используйте ID задачи для проверки статуса через API.\n\n"
                    f"_Примечание: в текущей версии бота нет команды для проверки статуса._\n"
                    f"_Используйте REST API: GET /task/{task.id}_",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard(True),
                )
            except Exception as e:
                logger.error(f"Ошибка отправки в RabbitMQ: {e}")
                task.status = "failed"
                task.error_message = f"Не удалось отправить задачу в очередь: {str(e)}"
                db.commit()
                
                await state.clear()
                await message.answer(
                    f"❌ Ошибка отправки задачи: {e}\n\n"
                    f"Задача создана (ID: {task.id}), но не была отправлена в очередь.",
                    reply_markup=get_main_keyboard(True),
                )
        else:
            # Fallback: если RabbitMQ недоступен, выполняем синхронно
            logger.warning("RabbitMQ недоступен, выполняем предсказание синхронно")
            
            prediction = calculate_prediction(
                total_debt=data["total_debt"],
                penalty_amount=data["penalty_amount"],
                days_overdue=data["days_overdue"],
                payments_ratio=data["payments_ratio"],
                is_physical_person=is_physical,
            )
            
            # Обновляем задачу
            task.status = "completed"
            task.prediction = prediction
            task.completed_at = datetime.now()
            db.commit()
            
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
                f"🔮 *Результат предсказания* (синхронный режим)\n\n"
                f"*Вероятность успеха:* {prediction:.1%}\n"
                f"*Вердикт:* {verdict}\n\n"
                f"📊 *Входные данные:*\n"
                f"• Сумма долга: {data['total_debt']:. 2f} руб.\n"
                f"• Пени: {data['penalty_amount']:. 2f} руб.\n"
                f"• Дней просрочки: {data['days_overdue']}\n"
                f"• Доля оплаченного: {data['payments_ratio']:. 1%}\n"
                f"• Физ. лицо: {'Да' if is_physical else 'Нет'}\n\n"
                f"💳 Списано: {model.price_credits} кредитов\n"
                f"💰 Остаток: {float(account.balance):.2f} кредитов",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard(True),
            )
    except Exception as e:
        logger.error(f"Ошибка обработки предсказания: {e}", exc_info=True)
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


# ============== Обработка неизвестных сообщений ==============
@router.message()
async def unknown_message(message: types. Message):
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
