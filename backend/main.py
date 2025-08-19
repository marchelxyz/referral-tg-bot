import asyncio
import logging
import os
import json

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from dotenv import load_dotenv

from sqlalchemy import String, BigInteger, select, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from aiohttp import web # Новая библиотека для веб-сервера

# --- Настройка ---
logging.basicConfig(level=logging.INFO)
load_dotenv()

# --- Настройка Базы Данных ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("Необходимо указать DATABASE_URL")

ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(ASYNC_DATABASE_URL, echo=True)
async_sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=True)
    deals: Mapped[list["Deal"]] = relationship(back_populates="agent")

# НОВАЯ МОДЕЛЬ СДЕЛКИ
class Deal(Base):
    __tablename__ = "deals"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_name: Mapped[str] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(50))
    agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    agent: Mapped["User"] = relationship(back_populates="deals")

# --- Настройка Бота ---
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# --- API Endpoint (Веб-сервер) ---
async def get_deals(request):
    """
    Эта функция будет вызываться, когда фронтенд запросит список сделок.
    """
    # TODO: В будущем мы будем получать telegram_id из запроса и фильтровать сделки
    # А пока отдаем тестовые данные
    deals_data = [
        {"id": 1, "client_name": "ООО Ромашка", "status": "Первичный контакт"},
        {"id": 2, "client_name": "ИП Васильев", "status": "Квалификация"},
        {"id": 3, "client_name": "John Doe", "status": "КП отправлено"},
    ]
    return web.Response(text=json.dumps(deals_data), content_type='application/json', headers={"Access-Control-Allow-Origin": "*"})

# --- Обработчики команд Бота ---
@dp.message(CommandStart())
async def handle_start(message: Message):
    # Код этой функции не изменился, просто убедитесь, что он на месте
    webapp_url = os.getenv("VERCEL_URL", "https.t.me")
    start_button = InlineKeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=webapp_url))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[start_button]])

    async with async_sessionmaker() as session:
        # ... (код регистрации пользователя остался без изменений)
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            new_user = User(telegram_id=message.from_user.id, full_name=message.from_user.full_name)
            session.add(new_user)
            await session.commit()
            greeting_text = f"👋 Привет, {new_user.full_name}!\n\nДобро пожаловать! Вы были успешно зарегистрированы."
        else:
            greeting_text = f"👋 С возвращением, {user.full_name}!"
    await message.answer(greeting_text, reply_markup=keyboard)

# --- Функции запуска ---
async def create_db_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def start_bot():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

async def start_api_server():
    app = web.Application()
    app.router.add_get("/api/deals", get_deals)
    runner = web.AppRunner(app)
    await runner.setup()
    # Railway предоставит порт в переменной окружения PORT
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', 8080)))
    await site.start()
    logging.info("API сервер запущен")
    # Эта задача будет работать вечно, пока не будет отменена
    await asyncio.Event().wait()

async def main():
    await create_db_tables()
    # Запускаем бота и API сервер параллельно
    await asyncio.gather(
        start_bot(),
        start_api_server()
    )

if __name__ == "__main__":
    asyncio.run(main())
