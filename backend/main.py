import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo
)

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, BigInteger, select

# --- Setup Logging and Environment ---
logging.basicConfig(level=logging.INFO)
load_dotenv()

# --- Database (SQLAlchemy) Setup ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("You must provide a DATABASE_URL in the environment variables")

# Explicitly tell SQLAlchemy to use the asyncpg driver
# by replacing "postgresql://" with "postgresql+asyncpg://"
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create the async engine to connect to the DB
engine = create_async_engine(ASYNC_DATABASE_URL, echo=True)

# Create a session factory for asynchronous work with the DB
# The function and the variable now have the same, correct name
async_sessionmaker = async_sessionmaker(engine, expire_on_commit=False)


# Define a base class for our models (tables)
class Base(DeclarativeBase):
    pass


# Describe the User model, which will correspond to the 'users' table in the DB
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=True)
    # TODO: Add referrer_id when referral logic is ready


# --- Bot Initialization ---
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()


# --- Command Handlers ---
@dp.message(CommandStart())
async def handle_start(message: Message):
    """
    Обрабатывает команду /start. Регистрирует нового пользователя и показывает кнопку Mini App.
    """
    # Считываем URL из переменных окружения. Если его нет, используется заглушка.
    webapp_url = os.getenv("VERCEL_URL", "https.t.me") # Резервный URL на случай ошибки
    
    start_button = InlineKeyboardButton(
        text="Открыть приложение", 
        web_app=WebAppInfo(url=webapp_url)
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[start_button]])

    async with async_sessionmaker() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()

        if user is None:
            new_user = User(
                telegram_id=message.from_user.id,
                full_name=message.from_user.full_name
            )
            session.add(new_user)
            await session.commit()
            greeting_text = (f"👋 Привет, {new_user.full_name}!\n\n"
                             "Добро пожаловать! Вы были успешно зарегистрированы.")
        else:
            greeting_text = (f"👋 С возвращением, {user.full_name}!")

    await message.answer(greeting_text, reply_markup=keyboard)

# --- Main Functions for Startup ---
async def create_db_tables():
    """
    Creates all database tables defined via Base.
    """
    async with engine.begin() as conn:
        # This command creates tables if they don't exist.
        # Otherwise, it does nothing.
        await conn.run_sync(Base.metadata.create_all)


async def main():
    """
    The main function to start the bot and create tables.
    """
    # 1. Create DB tables
    await create_db_tables()

    # 2. Start the bot
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
