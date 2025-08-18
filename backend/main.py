import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, BigInteger, select

# --- Настройка логирования и окружения ---
logging.basicConfig(level=logging.INFO)
load_dotenv()

# --- Настройка базы данных (SQLAlchemy) ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("Необходимо указать DATABASE_URL в переменных окружения")

# Явно указываем SQLAlchemy, что нужно использовать асинхронный драйвер asyncpg
# Мы просто заменяем "postgresql://" на "postgresql+asyncpg://"
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Создаем асинхронный "движок" для подключения к БД, используя новый URL
engine = create_async_engine(ASYNC_DATABASE_URL, echo=True)


# Определяем базовый класс для наших моделей (таблиц)
class Base(DeclarativeBase):
    pass


# Описываем модель User, которая будет соответствовать таблице 'users' в БД
class User(Base):
    __tablename__ = "users"

    # Колонки таблицы
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=True)
    # TODO: Добавить referrer_id, когда будет готова логика рефералов

# --- Инициализация бота ---
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()


# --- Обработчики команд (Handlers) ---
@dp.message(CommandStart())
async def handle_start(message: Message):
    """
    Обработчик команды /start. Регистрирует нового пользователя, если его еще нет.
    """
    # Открываем асинхронную сессию для работы с базой данных
    async with async_session_maker() as session:
        # Ищем пользователя в базе по его telegram_id
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()

        # Если пользователя нет, создаем и сохраняем его
        if user is None:
            new_user = User(
                telegram_id=message.from_user.id,
                full_name=message.from_user.full_name
            )
            session.add(new_user)
            await session.commit()
            greeting_text = (f"👋 Привет, {new_user.full_name}!\n\n"
                             "Рад видеть вас здесь. Вы были успешно зарегистрированы.")
        else:
            greeting_text = (f"👋 С возвращением, {user.full_name}!\n\n"
                             "Рад видеть вас снова.")

    # TODO: Добавить кнопку для открытия Mini App
    await message.answer(greeting_text)


# --- Основные функции для запуска ---
async def create_db_tables():
    """
    Создает все таблицы в базе данных, определенные через Base.
    """
    async with engine.begin() as conn:
        # Эта команда создает таблицы, если их не существует.
        # В противном случае, ничего не делает.
        await conn.run_sync(Base.metadata.create_all)


async def main():
    """
    Главная функция для запуска бота и создания таблиц.
    """
    # 1. Создаем таблицы в БД
    await create_db_tables()

    # 2. Запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
