import asyncio
import logging
import os
import json
from urllib.parse import parse_qs

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from dotenv import load_dotenv

from sqlalchemy import String, BigInteger, select, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from aiohttp import web

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

class Deal(Base):
    __tablename__ = "deals"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_name: Mapped[str] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(50), default="Первичный контакт")
    agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    agent: Mapped["User"] = relationship(back_populates="deals")

# --- Настройка Бота ---
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# --- Логика API (Веб-сервер) ---

async def get_user_from_auth_header(auth_header):
    """ Проверяет заголовок авторизации и возвращает пользователя из БД """
    if not auth_header or not auth_header.startswith('tma '):
        return None
    
    # Извлекаем и парсим initData
    init_data = auth_header.split(' ')[1]
    parsed_data = parse_qs(init_data)
    user_data_str = parsed_data.get('user', [None])[0]
    
    if not user_data_str:
        return None

    user_data = json.loads(user_data_str)
    telegram_id = user_data.get('id')

    async with async_sessionmaker() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

@web.middleware
async def cors_middleware(request, handler):
    """ Middleware для обработки CORS заголовков """
    if request.method == 'OPTIONS':
        response = web.Response()
    else:
        response = await handler(request)
    
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
    return response

async def get_deals(request):
    """ Отдает сделки для текущего пользователя """
    user = await get_user_from_auth_header(request.headers.get('Authorization'))
    if not user:
        return web.Response(status=401, text="Unauthorized")

    async with async_sessionmaker() as session:
        result = await session.execute(select(Deal).where(Deal.agent_id == user.id))
        deals = result.scalars().all()
        deals_data = [{"id": deal.id, "client_name": deal.client_name, "status": deal.status} for deal in deals]
        return web.json_response(deals_data)

async def create_deal(request):
    """ Создает новую сделку для текущего пользователя """
    user = await get_user_from_auth_header(request.headers.get('Authorization'))
    if not user:
        return web.Response(status=401, text="Unauthorized")

    data = await request.json()
    client_name = data.get('client_name')
    if not client_name:
        return web.Response(status=400, text="client_name is required")
    
    async with async_sessionmaker() as session:
        new_deal = Deal(client_name=client_name, agent_id=user.id)
        session.add(new_deal)
        await session.commit()
        await session.refresh(new_deal) # Чтобы получить id и другие поля
        return web.json_response({"id": new_deal.id, "client_name": new_deal.client_name, "status": new_deal.status})

# --- Обработчики команд Бота ---
# handle_start остается без изменений

@dp.message(CommandStart())
async def handle_start(message: Message):
    webapp_url = os.getenv("VERCEL_URL", "https.t.me")
    start_button = InlineKeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=webapp_url))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[start_button]])
    async with async_sessionmaker() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            new_user = User(telegram_id=message.from_user.id, full_name=message.from_user.full_name)
            session.add(new_user)
            await session.commit()
            greeting_text = f"👋 Привет, {new_user.full_name}!\n\nДобро пожаловать!"
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
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/api/deals", get_deals)
    app.router.add_post("/api/deals", create_deal) # Новый маршрут
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', 8080)))
    await site.start()
    logging.info("API сервер запущен")
    await asyncio.Event().wait()

async def main():
    await create_db_tables()
    await asyncio.gather(start_bot(), start_api_server())

if __name__ == "__main__":
    asyncio.run(main())
