from datetime import datetime
from io import StringIO
from aiogram.client.default import DefaultBotProperties, Default
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from cohere import Client
from aiogram.filters import Command
from aiogram import Bot, Dispatcher, types
import asyncio, logging, time, os


from config import *


async def edit_ans(msg: types.Message, temp: str, text: StringIO, logger: logging.Logger, i: int, start: float):
    if i % PROGRESS_STEP == 0:
        dots_count = (i // PROGRESS_STEP) % 4
        phase = (i // PROGRESS_STEP) % len(MOONS)
        secs = time.time() - start

        try:
            await msg.edit_text(
                f'{MOONS[phase]}{temp}{secs:.1f} сек{"." * dots_count}'
                f'\n\n{text.getvalue()}'
            )
        except TelegramBadRequest as e:
            await msg.edit_text(
                f'{MOONS[phase]}{temp}{secs:.1f} сек{"." * dots_count}'
            )
            logger.error(f'{text} | {e.message}')


async def main() -> None:
    logger = logging.getLogger(__name__)
    bot = Bot(token=BOT_API_TOKEN,
              default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher()
    chats = dict()

    @dp.message(Command(commands=['start']))
    async def start_message(msg: types.Message) -> None:
        await msg.answer('Ну приветики :) Я умею отвечать на вопросы и искать информацию в интернете.'
                         ' Попробуй команду **/web**!\n'
                         'Так же загляни на наш [GitHub!](https://github.com/rokokol/andromeda-i) 😌')
        await msg.delete()

    @dp.message(Command(commands=['help']))
    async def help_message(msg: types.Message) -> None:
        await msg.answer(
            COMMANDS,
            parse_mode=ParseMode.HTML
        )


    @dp.message(Command(commands=['web']))
    async def toggle_web(msg: types.Message) -> None:
        global is_web_search

        is_web_search = (is_web_search + 1) % 2
        if is_web_search:
            await msg.answer('Так и быть, теперь буду пользоваться всеми любимым **интернетом** при поиске ответа!')
        else:
            await msg.answer('Больше в **интернет** ни ногой...')


    @dp.message()
    async def conversation(msg: types.Message) -> None:
        user = msg.from_user.username
        mode = 'text-to-text' + (' + WEB' if is_web_search else '')
        context = chats.get(user, [])
        text = msg.text if msg.text is not None else ':)'
        temp = f' | {mode} | @{user} | '

        client = Client(client_name=user, api_key=COHERE_API_TOKEN)
        resp_stream = client.chat_stream(

            message=text,

            model="command-r-plus",

            preamble=PREAMBLE.format(user),

            chat_history=context,

            connectors=CONNECTORS[is_web_search]
        )

        resp_text = StringIO()
        start = time.time()
        reply = {
            'ans': await msg.answer(f'🌑{temp}отправка'),
            'search': None
        }
        is_searched = False
        search_text = '' # Иначе почему-то удаляются поисковые запросы
        for i, event in enumerate(resp_stream):
            await edit_ans(reply['ans'], temp, resp_text, logger, i, start)
            match event.event_type:  # TODO: сделать цитирование материалов при WEB и придумать способ обработки snippets

                case 'stream-start':
                    if is_web_search:
                        reply['search'] = await reply['ans'].reply('Ищу:')

                case 'search-queries-generation':
                    is_searched = True
                    queries = StringIO()
                    for query in event.search_queries:
                        queries.write(f'\n  🔍 {query.text}')

                    search_text = reply['search'].text + queries.getvalue()
                    await reply['search'].edit_text(search_text)

                case 'search-results':
                    results = StringIO()
                    results.write('\n\nНашел:')
                    for res in event.documents:
                        quote = LINK_CITE.format(res['title'], res['url'].strip())
                        results.write(f'\n  💡 {quote}')

                    await reply['search'].edit_text(search_text + results.getvalue())

                case 'text-generation':
                    resp_text.write(event.text)

                    if not is_searched and is_web_search:
                        await reply['search'].edit_text('Поиск не выполнялся 🤷')
                        is_searched = True

                case 'stream-end':
                    wasted_secs = time.time() - start
                    chats[user] = event.response.chat_history
                    logger.info(f'msg: {text} | by: {user} | response: {event.response.text}')

                    try:
                        await reply['ans'].edit_text(
                            f'🌕{temp}{wasted_secs:.1f} сек.'
                            f'\n\n{event.response.text}'
                        )
                    except TelegramBadRequest as e:
                        await reply['ans'].edit_text(
                            f'🌕{temp}{wasted_secs:.1f} сек.'
                            f'\n\n{event.response.text}',
                            parse_mode=Default("parse_mode")
                        )
                        logger.error(f'{text} | {e.message}')


    await dp.start_polling(bot)

if __name__ == "__main__":
    is_web_search = 0
    COHERE_API_TOKEN = str(os.getenv('COHERE_API_TOKEN'))
    BOT_API_TOKEN = str(os.getenv('ANDROMEDAI_API_TOKEN'))
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
