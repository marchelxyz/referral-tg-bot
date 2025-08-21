import asyncio
import logging
import os
import json
from urllib.parse import parse_qs
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from dotenv import load_dotenv

from sqlalchemy import String, BigInteger, select, ForeignKey, func, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from aiohttp import web

# --- Настройка и Модели Базы Данных (без изменений) ---
logging.basicConfig(level=logging.INFO)
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL: raise ValueError("Необходимо указать DATABASE_URL")

ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(ASYNC_DATABASE_URL, echo=True)
async_sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

# ... (все классы-модели: Base, User, Deal - остаются здесь без изменений) ...
class Base(DeclarativeBase): pass
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
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    checklist: Mapped[dict] = mapped_column(JSONB, nullable=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    agent: Mapped["User"] = relationship(back_populates="deals")

DEAL_FUNNEL_CHECKLISTS = {
    "Первичный контакт": [{"text": "Проверить корректность анкеты", "completed": False}, {"text": "Отметить клиента как «Первичный контакт»", "completed": False}],
    "Квалификация": [{"text": "Цель клиента понятна?", "completed": False}, {"text": "Есть бюджет?", "completed": False}, {"text": "Готов ли к звонку/встрече?", "completed": False}],
    "Презентация решения": [{"text": "КП отправлено", "completed": False}]
}

# --- Логика API и Бота (без изменений) ---
# ... (все функции: get_user_from_auth_header, cors_middleware, get_deals, create_deal, update_deal_status, toggle_checklist_item, handle_start - остаются здесь без изменений) ...
async def get_user_from_auth_header(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('tma '): return None
    init_data = auth_header.split(' ')[1]
    parsed_data = parse_qs(init_data)
    user_data_str = parsed_data.get('user', [None])[0]
    if not user_data_str: return None
    user_data = json.loads(user_data_str)
    telegram_id = user_data.get('id')
    async with async_sessionmaker() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        response = web.Response(status=200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
        return response
    try:
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except web.HTTPException as ex:
        ex.headers['Access-Control-Allow-Origin'] = '*'
        raise ex

async def get_deals(request):
    user = await get_user_from_auth_header(request)
    if not user: return web.Response(status=401, text="Unauthorized")
    async with async_sessionmaker() as session:
        result = await session.execute(select(Deal).where(Deal.agent_id == user.id).order_by(Deal.created_at.desc()))
        deals = result.scalars().all()
        deals_data = [{"id": deal.id, "client_name": deal.client_name, "status": deal.status, "checklist": deal.checklist} for deal in deals]
        return web.json_response(deals_data)

async def create_deal(request):
    user = await get_user_from_auth_header(request)
    if not user: return web.Response(status=401, text="Unauthorized")
    async with async_sessionmaker() as session:
        result = await session.execute(select(Deal).where(Deal.agent_id == user.id).order_by(Deal.created_at.desc()).limit(1))
        last_deal = result.scalar_one_or_none()
        if last_deal and datetime.utcnow() - last_deal.created_at < timedelta(minutes=1):
            return web.Response(status=429, text="Вы можете добавлять только одну сделку в минуту.")
        data = await request.json()
        client_name = data.get('client_name')
        if not client_name: return web.Response(status=400, text="client_name is required")
        initial_checklist = DEAL_FUNNEL_CHECKLISTS.get("Первичный контакт", [])
        new_deal = Deal(client_name=client_name, agent_id=user.id, checklist=initial_checklist)
        session.add(new_deal)
        await session.commit()
        await session.refresh(new_deal)
        return web.json_response({"id": new_deal.id, "client_name": new_deal.client_name, "status": new_deal.status, "checklist": new_deal.checklist})

async def update_deal_status(request):
    user = await get_user_from_auth_header(request)
    if not user: return web.Response(status=401, text="Unauthorized")
    deal_id = int(request.match_info['id'])
    data = await request.json()
    new_status = data.get('status')
    if not new_status: return web.Response(status=400, text="New status is required")
    async with async_sessionmaker() as session:
        result = await session.execute(select(Deal).where(Deal.id == deal_id, Deal.agent_id == user.id))
        deal = result.scalar_one_or_none()
        if not deal: return web.Response(status=404, text="Deal not found or you don't have permission")
        deal.status = new_status
        deal.checklist = DEAL_FUNNEL_CHECKLISTS.get(new_status, [])
        await session.commit()
        await session.refresh(deal)
        return web.json_response({"id": deal.id, "client_name": deal.client_name, "status": deal.status, "checklist": deal.checklist})

async def toggle_checklist_item(request):
    user = await get_user_from_auth_header(request)
    if not user: return web.Response(status=401, text="Unauthorized")
    deal_id = int(request.match_info['id'])
    data = await request.json()
    item_text = data.get('text')
    if not item_text: return web.Response(status=400, text="Checklist item text is required")
    async with async_sessionmaker() as session:
        result = await session.execute(select(Deal).where(Deal.id == deal_id, Deal.agent_id == user.id))
        deal = result.scalar_one_or_none()
        if not deal or not deal.checklist: return web.Response(status=404, text="Deal or checklist not found")
        new_checklist = []
        item_found = False
        for item in deal.checklist:
            if item.get('text') == item_text:
                item['completed'] = not item.get('completed', False)
                item_found = True
            new_checklist.append(item)
        if not item_found: return web.Response(status=404, text="Checklist item not found")
        deal.checklist = new_checklist
        await session.commit()
        await session.refresh(deal)
        return web.json_response(deal.checklist)

dp = Dispatcher()
@dp.message(CommandStart())
async def handle_start(message: Message):
    bot = message.bot
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


# --- НОВАЯ, УЛУЧШЕННАЯ ЛОГИКА ЗАПУСКА ---

async def on_startup(app: web.Application):
    """Действия при старте веб-сервера."""
    logging.info("Веб-сервер запускается...")
    # Создаем таблицы в БД
    await create_db_tables()
    # Запускаем бота в фоновой задаче
    bot_token = os.getenv("BOT_TOKEN")
    bot = Bot(token=bot_token)
    app['bot_task'] = asyncio.create_task(dp.start_polling(bot))
    logging.info("Бот запущен в фоновом режиме.")

async def on_shutdown(app: web.Application):
    """Действия при остановке веб-сервера."""
    logging.info("Веб-сервер останавливается...")
    # Останавливаем бота
    app['bot_task'].cancel()
    logging.info("Бот остановлен.")

async def create_db_tables():
    """Создает таблицы в БД, если их нет."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Основная точка входа
if __name__ == "__main__":
    # Создаем приложение веб-сервера
    app = web.Application(middlewares=[cors_middleware])
    
    # Регистрируем функции, которые должны выполниться при старте и остановке
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Добавляем маршруты API
    app.router.add_get("/api/deals", get_deals)
    app.router.add_post("/api/deals", create_deal)
    app.router.add_post("/api/deals/{id}/status", update_deal_status)
    app.router.add_post("/api/deals/{id}/checklist", toggle_checklist_item)

    # Запускаем веб-сервер. Он будет главным процессом.
    web.run_app(app, host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
