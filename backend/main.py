import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

# Включаем логирование, чтобы видеть сообщения в консоли
logging.basicConfig(level=logging.INFO)

# Загружаем переменные окружения из файла .env
load_dotenv()

# Инициализация бота и диспетчера
# Мы получаем токен бота из переменных окружения
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# --- Обработчики команд (Handlers) ---

@dp.message(CommandStart())
async def handle_start(message: Message):
    """
    Этот обработчик будет отвечать на команду /start.
    """
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    
    # args = message.text.split()
    # if len(args) > 1:
    #     referrer_id = args[1]
    #     # TODO: Здесь будет логика обработки реферальной ссылки
    #     # Например, сохранение связи "кто кого пригласил" в базу данных
    
    # TODO: Здесь будет логика регистрации или входа пользователя в базу данных
    
    text = (f"👋 Привет, {full_name}!\n\n"
            "Добро пожаловать в нашу реферальную систему.\n\n"
            "Скоро здесь появится главное меню для управления сделками и финансами.")

    await message.answer(text)

# --- Основная функция для запуска бота ---

async def main():
    """
    Главная асинхронная функция для запуска бота.
    """
    # Пропускаем накопившиеся апдейты при запуске
    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем поллинг - постоянный опрос серверов Telegram на наличие новых сообщений
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Запускаем основную функцию `main`
    asyncio.run(main())
