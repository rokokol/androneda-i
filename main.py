from cohere import Client, Message_User, Message_Chatbot
from aiogram.filters import Command
from aiogram import Bot, Dispatcher, types
import asyncio, logging

from config import *
from tokens import *


async def main() -> None:
    logger = logging.getLogger(__name__)
    bot = Bot(token=BOT_API_TOKEN)
    dp = Dispatcher()
    chats = dict()

    @dp.message(Command(commands=['start']))
    async def start_message(msg: types.Message) -> None:
        await msg.answer('Ну приветики :) Пока что я умею только text-to-text, поэтому напиши мне что-то интересное')
        await msg.delete()

    @dp.message(Command(commands=['help']))
    async def help_message(msg: types.Message) -> None:
        await msg.answer('Мне лень писать, просто взгляни [сюда](https://github.com/rokokol/loaf-ai) 😌',
                         parse_mode='Markdown')

    @dp.message()
    async def conversation(msg: types.Message) -> None:
        user = msg.from_user.username
        context = chats.get(user, [])
        text = msg.text if msg.text is not None else ':)'

        client = Client(client_name=user, api_key=COHERE_API_TOKEN)
        resp = dict(client.chat(

            message=text,

            model="command-r-plus",

            preamble=PREAMBLE,

            chat_history=context

        ))['text']

        context.append(Message_User(message=text))
        context.append(Message_Chatbot(message=resp))
        chats[user] = context
        logger.info(f'msg: {text} | by: {user} | response: {resp}')

        await msg.answer(resp, parse_mode='Markdown')

    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename='log.log',
        filemode='w'
    )
    asyncio.run(main())
