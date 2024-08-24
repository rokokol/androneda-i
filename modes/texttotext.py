import logging
import time
import json
from aiogram import types
from io import StringIO
from aiogram.client.default import Default
from aiogram.exceptions import TelegramBadRequest
from cohere import Client
from config import *


logger = logging.getLogger(__name__)


async def __edit_ans(msg: types.Message, temp: str, text: StringIO, i: int, start: float) -> None:
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


async def text_to_text(msg: types.Message, client: Client, modes: set, user: str) -> None:
    """
    Текстовый ответ на текстовый запрос. Может также работать и с WEB модом
    :param msg: сообщение пользователя
    :param client: Cohere клиент с ключем
    :param modes: список режимов
    :param user: пользователь, который отправил сообщение
    :return: True если завершилось удачно, иначе False
    """
    prompt = msg.text if msg.text is not None else ':)'
    modeline = ' + '.join([i.value[0] for i in list(modes)])
    temp = f' | {modeline} | @{user} | '
    is_web_search = 1 if Modes.WEB in modes else 0
    chat = deserialize_from_json('src/users').get(user, user)

    resp_stream = client.chat_stream(

        message=prompt,

        model="command-r-plus",

        preamble=PREAMBLE.format(user),

        conversation_id=chat,

        connectors=CONNECTORS[is_web_search],
    )

    resp_text = StringIO()
    start = time.time()
    reply = {
        'ans': await msg.answer(f'🌑{temp}отправка'),
        'search': None
    }
    is_searched = False
    search_text = ''  # Иначе почему-то удаляются поисковые запросы

    for i, event in enumerate(resp_stream):
        await __edit_ans(reply['ans'], temp, resp_text, i, start)
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

                logger.info(
                    f'msg: {prompt} | by: {user} | response: {event.response.text}')
