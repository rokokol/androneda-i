from datetime import datetime
from random import randint

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram import Bot, Dispatcher, types
import asyncio
import logging
import os
from cohere import Client
from holoviews.operation import chain

from modes import texttotext
from config import *


async def main() -> None:
    bot = Bot(token=BOT_API_TOKEN,
              default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher()

    @dp.message(Command(commands=['start']))
    async def start_message(msg: types.Message) -> None:
        await msg.answer('Ну приветики :) Я умею отвечать на вопросы и искать информацию в интернете.'
                         ' Попробуй команду **/web**!\n'
                         'Так же загляни на наш [GitHub!](https://github.com/rokokol/andromeda-i) 😌')

        user = msg.from_user.username
        chats = deserialize_from_json('src/users')
        chats[user] = f'{user}{randint(1, 100000)}'
        serialize_to_json(chats, 'src/users')
        await msg.delete()

    @dp.message(Command(commands=['help']))
    async def help_message(msg: types.Message) -> None:
        await msg.answer(
            COMMANDS,
            parse_mode=ParseMode.HTML
        )

    @dp.message(Command(commands=['web']))
    async def toggle_web(msg: types.Message) -> None:
        if Modes.WEB in modes:
            modes.remove(Modes.WEB)
            await msg.answer('Больше в **интернет** ни ногой...')
        else:
            modes.add(Modes.WEB)
            await msg.answer('Так и быть, теперь буду пользоваться всеми любимым **интернетом** при поиске ответа!')

    @dp.message()
    async def conversation(msg: types.Message) -> None:
        user = msg.from_user.username
        client = Client(client_name=user, api_key=COHERE_API_TOKEN)

        if Modes.TEXTTOTEXT in modes:
            await texttotext.text_to_text(msg, client, modes, user)

    await dp.start_polling(bot)


if __name__ == "__main__":
    modes = {Modes.TEXTTOTEXT}
    COHERE_API_TOKEN = str(os.getenv('COHERE_API_KEY'))
    BOT_API_TOKEN = str(os.getenv('ANDROMEDAI_API_KEY'))
    today = datetime.today()
    os.makedirs('logs', exist_ok=True)

    if TEST:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=f'logs/{today.day}.{today.month}.{today.year}.log',
            filemode='a'
        )

    asyncio.run(main())
