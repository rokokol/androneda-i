from datetime import datetime

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from cohere import Client
from aiogram.filters import Command
from aiogram import Bot, Dispatcher, types
import asyncio, logging, time, os

from config import *


async def main() -> None:
    logger = logging.getLogger(__name__)
    bot = Bot(token=BOT_API_TOKEN,
              default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher()
    chats = dict()

    @dp.message(Command(commands=['start']))
    async def start_message(msg: types.Message) -> None:
        await msg.answer('Ну приветики :) Пока что я умею только text-to-text, поэтому напиши мне что-то интересное')
        await msg.delete()

    @dp.message(Command(commands=['help']))
    async def help_message(msg: types.Message) -> None:
        await msg.answer('Мне лень писать, просто взгляни [сюда](https://github.com/rokokol/andromeda-i) 😌',
                         ParseMode.MARKDOWN)

    @dp.message()
    async def conversation(msg: types.Message) -> None:
        user = msg.from_user.username
        context = chats.get(user, [])
        text = msg.text if msg.text is not None else ':)'
        temp = f' | text-to-text | @{user} | '

        client = Client(client_name=user, api_key=COHERE_API_TOKEN)
        resp_stream = client.chat_stream(

            message=text,

            model="command-r-plus",

            preamble=PREAMBLE,

            chat_history=context,

        )

        start = time.time()
        ans = await msg.answer(f'🌑{temp}отправка')
        for i, event in enumerate(resp_stream):
            if event.event_type != 'stream-end':
                if i % PROGRESS_STEP == 0:
                    dots_count = (i // PROGRESS_STEP) % 4
                    phase = (i // PROGRESS_STEP) % len(MOONS)
                    await ans.edit_text(
                        f'{MOONS[phase]}{temp}печатаю{"." * dots_count}'
                    )
            else:
                wasted_secs = time.time() - start
                await ans.edit_text(
                    f'🌕{temp}{wasted_secs:.1f} сек.'
                    f'\n\n{event.response.text}'
                )
                chats[user] = event.response.chat_history
                logger.info(f'msg: {text} | by: {user} | response: {event.response.text}')


    await dp.start_polling(bot)

if __name__ == "__main__":
    COHERE_API_TOKEN = str(os.getenv('COHERE_API_TOKEN'))
    BOT_API_TOKEN = str(os.getenv('ANDROMEDAI_API_TOKEN'))
    today = datetime.today()
    os.makedirs('logs', exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=f'logs/{today.day}.{today.month}.{today.year}.log',
        filemode='a'
    )
    asyncio.run(main())
