import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
import requests
import re
import shutil
import random
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.filters.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums.parse_mode import ParseMode
from aiogram.types import InlineKeyboardButton, CallbackQuery, FSInputFile, InlineKeyboardMarkup
import aiomysql
import asyncio
import telegram_music_quiz_bot.bot.keyboards as kb
import logging
import secrets
from copy import deepcopy
from transformers import LlamaForCausalLM, AutoTokenizer
from openai import OpenAI
import aiohttp
import json
import telegram_music_quiz_bot.vector_search as vector_search
import search
import rag_genius
from redis.asyncio import Redis


CLIENT_ID = os.getenv('CLIENT_ID')
TG_TOKEN = os.getenv('TG_TOKEN')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
PASSWORD = os.getenv('PASSWORD')
dp = Dispatcher()
router_add_song = Router()
router_add_pl = Router()
router_delete_song = Router()
router_delete_playlist = Router()
router_quiz = Router()
router_get = Router()
router_search = Router()
router_edit = Router()
dp.include_routers(router_add_pl, router_edit, router_add_song, router_delete_song, router_delete_playlist,
                     router_quiz, router_get, router_search)
bot = Bot(token=TG_TOKEN)
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID,
                                                           client_secret=CLIENT_SECRET))
logger = logging.Logger(__name__)
cur_playlists = {}
songs_left = {}
questions_left = {}
max_amount = {}
points = {}
max_points = {}
correct_options_dict = {}
inviters_info = {}
songs_all = {}
quiz_type = {}
counter = 0
users_seeds = {}
generated_questions = {}

# tokenizer = AutoTokenizer.from_pretrained('meta-llama/Meta-Llama-3.1-8B-Instruct') 
# model = LlamaForCausalLM.from_pretrained('meta-llama/Meta-Llama-3.1-8B-Instruct')

client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
redis_pool = Redis()

async def get_song_preview_url(song_id):
    track_info = sp.track(song_id)
    print(track_info['artists'])
    artists = ", ".join([artist['name'] for artist in track_info['artists']])
    return track_info['preview_url'], artists + " - " + track_info['name']

async def download_preview(url, filename):
    response = requests.get(url)
    with open(filename, 'wb') as file:
        file.write(response.content)

async def extract_spotify_track_id(url):
    match = re.search(r'https://open\.spotify\.com/track/([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    else:
        return None
    
async def inline_lists(lst, ids, param, menu=True):
    keyboard = InlineKeyboardBuilder()
    for i, inst in enumerate(lst):
        keyboard.button(text=inst, callback_data=f'{ids[i]} {param}')
    keyboard.button(text='Back to menu', callback_data='menu')
    keyboard = keyboard.adjust(*[1]*len(lst))
    return keyboard.as_markup()

async def retrieve_data(sql_query, cache_key):
    if not await redis_pool.exists(cache_key): 
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql_query)
                result = list(zip(*(await cursor.fetchall())))
    else:
        result = json.loads(await redis_pool.get(cache_key))
    if isinstance(result, list):
        if len(result[0]) == 1:
            result = [field[0] for field in result]
    return result if result else None

async def generate_unique_token():
    return secrets.token_hex(32)

async def generate_question(prompt, url, model):
    async with aiohttp.ClientSession() as session:
        payload = {
            'model': model,
            'messages': [{"role": "system", "content": '''You are a bot for creating questions for music quizes. You always answer in json output format with a question, 4 options and 1 correct answer like this: {"question": your_generated_question, "options": your_generated_options, "correct_answer": your_generated_correct_answer}'''},
                         {"role": "user", "content": prompt}],
            'temperature': 0.9,
            'max_tokens': 200, 
            'example_output': '''Q: Create a question-interesting fact for a music quiz with 4 possible options with only 1 answer for this song: Melanie Martinez - Tag, You're it.
                    A:{{"question": "What is the album that Melanie Martinez released in 2015, and the song 'Tag, You're it' belongs to it?", "options": ["Crybaby", "Dollhouse", "K-12", "Portals"], "correct_answer": "Crybaby"'}}
                    
                    Q: Create a question-interesting fact for a music quiz with 4 possible options with only 1 answer for this song: Coldplay - Viva La Vida.
                    A:{{"question": "In Coldplay's song 'Viva La Vida' what does the narrator claim he used to rule?", "options": ["The seas", "The world", "The skies", "The people"], "correct_answer": "The world"'}}
                    
                    Q: Create a question-interesting fact for a music quiz with 4 possible options with only 1 answer for this song: Eminem - Mockingbird.
                    A:{{"question": "In Eminem's song 'Mockingbird' who is he primarily addressing in the lyrics?", "options": ["His mother", "His ex-wife", "His fans", "His daughters"], "correct_answer": "His daughters"'}}
                    
                    Q: Create a question-interesting fact for a music quiz with 4 possible options with only 1 answer for this song: {correct_option}.
                    '''
        }
        async with session.post(url, json=payload) as response:
            result = await response.json()
            return result['choices'][0]["message"]['content']

class Form(StatesGroup):
    waiting_for_song_id = State()
    waiting_for_playlist_name = State()
    menu = State()
    got_amount = State()
    invite_link = State()
    other_playlist_got_amount = State()
    waiting_for_amount = State()
    waiting_for_description = State()
    waiting_for_search_query = State()
    search_got_amount = State()
    edit_playlist_name = State()
    edit_playlist_desc= State()

@dp.message(CommandStart())
async def send_welcome(message, state):
    username = message.from_user.username
    args = message.text.split()
    user_id = message.from_user.id
    if len(args) > 1:
        username = message.from_user.username
        logger.info("QUIZ SHARE", extra={'user': username})

        token = args[-1]
        if songs_left.get(user_id):
            songs_left.pop(user_id, None)
            songs_all.pop(user_id, None)
            correct_options_dict.pop(user_id, None)
            quiz_type.pop(user_id, None)
            points.pop(user_id, None)
            cur_playlists.pop(user_id, None)
            max_points.pop(user_id, None)
            questions_left.pop(user_id, None)
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                cache_key = f'share_info:{token}'
                if await redis_pool.exists(cache_key):
                    share_info = await json.loads(redis_pool.get(cache_key))
                    cur_playlists[user_id] = share_info['playlist_id']
                    inviter_user_id = share_info['user_id']
                    quiz_type[user_id] = share_info['quis_type']
                    max_points[user_id] = share_info['max_points']
                    users_seeds[user_id] = share_info['seed']
                else:
                    await bot.send_message(user_id, text="You've been invited to complete a quiz from your friend! Sorry the link has expired, ask your friend for generating a new one.",
                                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                                        InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
                    return
                print(max_points)
                inviters_info[user_id] = inviter_user_id
                questions_left[user_id] = max_points[user_id]
                points[user_id] = 0

                await message.answer(text=f"Hello {username}! You've been invited to complete a quiz from your friend! Press the button below to start quiz",
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Start quiz', callback_data=f' quiz')]]))
                
    else:
        logger.info("START", extra={'user': username})
        instruction = ""
        with open('instruction.txt', 'r') as f:
            lines = f.readlines()
            for line in lines:
                instruction += line
        
        await bot.send_message(user_id, text=f'''Hello {username}\! It's a bot for creating music quizes\. \
                               Do not forget to challenge your friends\!\n\n''' + instruction,
                               reply_markup=kb.main,
                               parse_mode=ParseMode('MarkdownV2'))

@dp.callback_query(F.data=='instruction')
async def instruction(callback: CallbackQuery, state):
    user_id = callback.from_user.id
    username = callback.from_user.username
    logging.info('INSTRUCTION', extra={'user': username})
    instruction = ""
    with open('instruction.txt', 'r') as f:
        lines = f.readlines()
        for line in lines:
            instruction += line
    await bot.send_message(user_id, text=instruction, 
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                        InlineKeyboardButton(text='Back to menu', callback_data='menu')]]),
                           parse_mode=ParseMode('MarkdownV2'))
@dp.callback_query(F.data=='menu')
async def send_menu(message, state):
    user_id = message.from_user.id
    songs_left.pop(user_id, None)
    songs_all.pop(user_id, None)
    correct_options_dict.pop(user_id, None)
    quiz_type.pop(user_id, None)
    points.pop(user_id, None)
    cur_playlists.pop(user_id, None)
    max_points.pop(user_id, None)
    questions_left.pop(user_id, None)
    users_seeds.pop(user_id, None)
    username = message.from_user.username
    logger.info("MENU", extra={'user': username})
    await state.clear()
    await bot.send_message(user_id, text=f'''Choose an option:''',
                         reply_markup=kb.main)
    
@router_edit.callback_query(F.data=='edit_playlist')
async def edit_playlist(callback: CallbackQuery, state):
    user_id = callback.from_user.id
    username = callback.from_user.username
    logging.info("EDIT PLAYLIST", extra={'user': username})
    cache_key = f'user:{user_id}'
    result = await retrieve_data(sql_query=f"SELECT id, name FROM playlists WHERE user_id='{callback.from_user.id}'",
                                 cache_key=cache_key)
    if isinstance(result, dict):
        playlists_ids, playlists_names = list(zip(*json.loads(result['playlists'])))
    elif isinstance(result, list):
        playlists_ids, playlists_names = result 
        await redis_pool.set(cache_key, json.dumps({"playlists": list(zip(playlists_ids, playlists_names)),
                                                    "username": username}), ex=1200)
    else:
        playlists_ids = []
    if not playlists_ids:
        await bot.send_message(user_id, text="You don't have any playlists in your library, so you can't delete anything. \
                               Please create a playlist to interact with it.",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                            InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
        return 
    await bot.send_message(callback.from_user.id, text=f'Choose the playlist from your library to edit it:', 
                           reply_markup=(await inline_lists(playlists_names, playlists_ids, "edit_playlist_chosen")))
    
@router_edit.callback_query(F.data.endswith('edit_playlist_chosen'))
async def edit_playlist_chosen(callback: CallbackQuery, state):
    username = callback.from_user.username
    user_id = callback.from_user.id
    playlist_id = callback.data.split()[0]
    logging.info("EDIT PLAYLIST CHOOSE OPTION", extra={'user': username})
    cur_playlists[user_id] = playlist_id
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            cache_key = f'playlist:{playlist_id}'
            if not await redis_pool.exists(cache_key):
                await cursor.execute(f"SELECT name, is_public, description FROM playlists WHERE id={playlist_id}")
                playlist_name, is_public, description = await cursor.fetchone()
                await redis_pool.set(cache_key, json.dumps({"name": playlist_name,
                                                            "user_id": user_id,
                                                            "is_public": is_public,
                                                            "description": description}), ex=1200)
            else:
                json_info = json.loads(await redis_pool.get(cache_key))
                playlist_name = json_info['name']
                is_public = json_info['is_public']
                description = json_info['description']
            visibility = 'public' if is_public else 'private'
    await bot.send_message(callback.from_user.id, text=f'Name: {playlist_name}\n\nDescription: {description}\n\nVisibility: {visibility}\n\nChoose either you want to edit name, discription or visibility:', 
                           reply_markup=(await inline_lists(['Name', 'Description', 'Visibility'], 
                                                            [0, 1, 2], "edit_playlist_option_chosen")))
    
@router_edit.callback_query(F.data.endswith('edit_playlist_option_chosen'))
async def edit_playlist_option_chosen(callback: CallbackQuery, state):
    user_id = callback.from_user.id
    username = callback.from_user.username
    logging.info("CHANGE INFO", extra={'user': username})
    option = int(callback.data.split()[0])
    playlist_id = cur_playlists[user_id]
    print(option)
    if option == 0:
        await bot.send_message(user_id, text=f'Please enter a new name for your playlist:',
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
        await state.set_state(Form.edit_playlist_name)
    elif option == 1:
        await bot.send_message(user_id, text=f'Please enter a new description for your playlist:',
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
        await state.set_state(Form.edit_playlist_desc)
    else:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                cache_key = f'playlist:{playlist_id}'
                if not await redis_pool.exists(cache_key):
                    await cursor.execute(f"SELECT is_public FROM playlists WHERE id={playlist_id}")
                    is_public = (await cursor.fetchone())[0]
                else:
                    json_info = json.loads(await redis_pool.get(cache_key))
                    playlist_name = json_info['name']
                    is_public = json_info['is_public']
                    description = json_info['description']
                    await redis_pool.delete(cache_key)
                
                await cursor.execute(f"UPDATE playlists SET is_public={not is_public}")
                await conn.commit()

        reply = 'Private' if is_public else 'Public'
        if is_public:
            await search.delete_playlist(playlist_id)
        else:
            await search.add_playlist(playlist_id, playlist_name, username, description)

        await bot.send_message(user_id, text=f'Your playlist is now {reply}.',
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))

@router_edit.message(Form.edit_playlist_name)
async def edit_playlist_chosen(message, state):
    user_id = message.from_user.id
    username = message.from_user.username
    logging.info("CHANGE NAME", extra={'user': username})
    new_name = message.text
    playlist_id = cur_playlists[user_id]
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            cache_key = f'playlist:{playlist_id}'
            if not await redis_pool.exists(cache_key):
                await cursor.execute(f"SELECT name FROM playlists WHERE id={playlist_id}")
                cur_playlist_name = (await cursor.fetchone())[0]
            else:
                json_info = json.loads(await redis_pool.get(cache_key))
                cur_playlist_name = json_info['name']
                await redis_pool.delete(cache_key)

            await cursor.execute(f'''UPDATE playlists SET name="{new_name}" WHERE id={playlist_id}''')
            await search.update(id=playlist_id, field='name', value=new_name)
            await vector_search.update_name(playlist_name=cur_playlist_name, user_id=str(user_id), new_name=new_name)
            await conn.commit()
    await bot.send_message(user_id, text=f'Name of the playlist was succesfully changed to {new_name}',
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))

@router_edit.message(Form.edit_playlist_desc)
async def edit_playlist_chosen(message, state):
    user_id = message.from_user.id
    username = message.from_user.username
    logging.info("CHANGE DESCRIPTION", extra={'user': username})
    new_desc = message.text
    playlist_id = cur_playlists[user_id]
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            cache_key = f'playlist:{playlist_id}'
            await cursor.execute(f'''UPDATE playlists SET description="{new_desc}" WHERE id={playlist_id}''')
            await search.update(id=playlist_id, field='description', value=new_desc)
            await conn.commit()
            await redis_pool.delete(cache_key)
    await bot.send_message(user_id, text=f'Description of the playlist was succesfully changed to {new_desc}',
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    
@router_search.callback_query(F.data=='search')
async def perform_search(callback: CallbackQuery, state):
    user_id = callback.from_user.id
    username = callback.from_user.username
    logger.info('SEARCH', extra={'user': username})
    await bot.send_message(user_id, text='Search other playlists by their name, description or username of the creator:',
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    await state.set_state(Form.waiting_for_search_query)

@router_search.message(Form.waiting_for_search_query)
async def got_query(message, state):
    user_id = message.from_user.id
    query = message.text
    top_playlists_info = await search.search(['name', 'username', 'description'], query)
    ids = []
    top_playlists = []
    print(top_playlists_info)
    for playlist in top_playlists_info:
        ids.append(playlist['_id'])
        top_playlists.append(playlist['_source']['name'] + " by " + str(playlist['_source']['username']))
    if ids:
        await bot.send_message(user_id, text='Here are the results of the search:',
                                reply_markup=await inline_lists(top_playlists, ids=ids, param='search'))
        await state.clear()
    else:
        await bot.send_message(user_id, text='There are no playlists that match your query, please try again typing your search:',
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))

@router_search.callback_query(F.data.endswith(' search'))
async def playlist_chosen(callback: CallbackQuery, state):
    user_id = callback.from_user.id
    playlist_id = int(callback.data.split()[0])
    print(playlist_id)
    cur_playlists[user_id] = playlist_id
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            cache_key = f'playlist:{playlist_id}'
            result = await retrieve_data(sql_query=f"SELECT name, is_public, description, user_id FROM playlists WHERE id={playlist_id}",
                                 cache_key=cache_key)
            if isinstance(result, dict):
                playlist_name = result['name']
                playlist_user_id = result['user_id']
                description = result['description']
            elif isinstance(result, list):
                playlist_name, is_public, description, playlist_user_id = result 
                await redis_pool.set(cache_key, json.dumps({"name": playlist_name,
                                                            "user_id": user_id,
                                                            "is_public": is_public,
                                                            "description": description}), ex=1200)
            cache_key = f'user:{playlist_user_id}'
            if not await redis_pool.exists(cache_key):
                await cursor.execute(f"SELECT username FROM users WHERE id={playlist_user_id}")
                playlist_creator_username = (await cursor.fetchone())[0]
                await redis_pool.set(cache_key, json.dumps({"username": playlist_creator_username}), ex=1200)
            else:
                json_info = json.loads(await redis_pool.get(cache_key))
                playlist_creator_username = json_info['username']

    await bot.send_message(user_id, text=f'{playlist_name} by {playlist_creator_username}.\n{description}\n Do you want to attempt quiz based on this playlist?', 
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                               [InlineKeyboardButton(text='Attempt quiz', callback_data='search_quiz')],
                               [InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))

@router_search.callback_query(F.data == 'search_quiz')
async def quiz_attempt(callback: CallbackQuery, state):
    user_id = callback.from_user.id
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SELECT COUNT(name) FROM songs WHERE playlist_id={cur_playlists[user_id]}")
            max_amount[user_id] = (await cursor.fetchone())[0]
            print(max_amount[user_id])
    await bot.send_message(user_id, text=f'Please enter amount of questions in the quiz(less than or equal {max_amount[user_id]}):',
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    await state.set_state(Form.search_got_amount)

@router_search.message(Form.search_got_amount)
async def quiz_attempt_got_amount(message, state):
    user_id = message.from_user.id
    if message.text.isdigit():
        amount = int(message.text)
    else:
        await bot.send_message(user_id, text='Please enter a valid number:')
        return
    if amount < max_amount[user_id]:
        await bot.send_message(user_id, text='This playlist does not contain such amount of questions. Please provide a new amount:')
        return
    print(amount)
    max_points[user_id] = amount
    questions_left[user_id] = max_points[user_id]
    points[user_id] = 0
    await bot.send_message(user_id, text='Choose the type of quiz: ',
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                               [InlineKeyboardButton(text='Guess the song', callback_data='melody quiz')],
                               [InlineKeyboardButton(text='Facts about song', callback_data='facts quiz')],
                               [InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))

@router_add_pl.callback_query(F.data=='create_playlist')
async def ask_for_playlist_name(callback: CallbackQuery, state):
    username = callback.from_user.username
    logger.info("CREATE PLAYLIST", extra={'user': username})
    await bot.send_message(callback.from_user.id, "Please provide a name of new playlist:", 
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    await state.set_state(Form.waiting_for_playlist_name)

@router_add_pl.message(Form.waiting_for_playlist_name)
async def create_playlist(message, state):
    await state.clear()
    cur_playlists[message.from_user.id] = {'name': message.text}
    await bot.send_message(message.from_user.id, "Please provide a description for your playlist:",
                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    await state.set_state(Form.waiting_for_description)

@router_add_pl.message(Form.waiting_for_description)
async def create_playlist(message, state):
    await state.clear()
    cur_playlists[message.from_user.id]['description'] = message.text
    await bot.send_message(message.from_user.id, "Will it be public or private playlist?",
                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Public", callback_data='public got_visibility')], 
                                                        [InlineKeyboardButton(text="Private", callback_data='private got_visibility')],
                                                        [InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))

@router_add_pl.callback_query(F.data.endswith(' got_visibility'))
async def create_playlist(callback, state):
    
    visibility = callback.data.split()[0]
    username = callback.from_user.username
    visibility = 1 if visibility == 'public' else 0
    user_id = callback.from_user.id
    playlist_name = cur_playlists[user_id]['name']
    description = cur_playlists[user_id]['description']
    cur_playlists.pop(user_id)
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"INSERT INTO playlists(name, user_id, is_public, description) VALUES('{playlist_name}', {user_id}, {visibility}, '{description}');")
            await conn.commit()
            await redis_pool.delete(f'user:{user_id}')
            await cursor.execute(f"SELECT id FROM playlists WHERE name='{playlist_name}' AND user_id={user_id}")
            playlist_id = (await  cursor.fetchone())[0]
            playlist_info = {
                "name": playlist_name,
                "user_id": user_id,
                "is_public": visibility,
                "description": description
            }
            await redis_pool.set(f"playlist:{playlist_id}", str(playlist_info), ex=1200)
    await bot.send_message(user_id, text=f"Playlist {playlist_name} was created successfully!",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                        InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))

@router_add_song.callback_query(F.data=='add_song')
async def ask_for_song_id(callback: CallbackQuery, state):
    username = callback.from_user.username
    user_id = callback.from_user.id
    logger.info("CHOOSE PLAYLIST", extra={'user': username})
    cache_key = f'user:{user_id}'
    result = await retrieve_data(sql_query=f"SELECT id, name FROM playlists WHERE user_id='{callback.from_user.id}'",
                                 cache_key=cache_key)
    if isinstance(result, dict):
        playlists_ids, playlists_names = list(zip(*result['playlists']))
    elif isinstance(result, list):
        playlists_ids, playlists_names = result 
        await redis_pool.set(cache_key, json.dumps({"playlists": list(zip(playlists_ids, playlists_names)),
                                                    "username": username}), ex=1200)
    else:
        playlists_ids = []
    if not playlists_ids:
        await bot.send_message(user_id, text="You don't have any playlists in library. Please create a one to start adding songs to it.",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                        InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
        return
    await bot.send_message(user_id, text=f'Choose the playlist from your library to add a song:', 
                           reply_markup=(await inline_lists(playlists_names, playlists_ids, "playlist_add")))

@router_add_song.callback_query(F.data.endswith(' playlist_add'))
async def got_playlist(callback, state):
    username = callback.from_user.username
    logger.info("PROVIDE SONG ID", extra={'user': username})
    await bot.send_message(callback.from_user.id, "Please provide a song link from spotify:",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    await state.set_state(Form.waiting_for_song_id)
    cur_playlists[callback.from_user.id] = " ".join(callback.data.split()[:-1])

@router_add_song.message(Form.waiting_for_song_id)
async def add_song_to_playlist(message, state):
    username = message.from_user.username
    logger.info("ADD SONG", extra={'user': username})
    user_id = message.from_user.id
    try:
        spotify_url = message.text.strip()
        cache_key = f'song_url:{spotify_url}'
        preview_url = '123'
        if not await redis_pool.exists(cache_key):
            song_id = await extract_spotify_track_id(spotify_url)
            preview_url, song_name = await get_song_preview_url(song_id)
        else:
            json_info = json.loads(await redis_pool.get(cache_key))
            song_id = json_info['id']
            song_name = json_info['name']

        playlist_id = cur_playlists[message.from_user.id]

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                cache_key = f'playlist:{playlist_id}'
                result = await retrieve_data(sql_query=f"SELECT name, is_public, description FROM playlists WHERE id={playlist_id}",
                                 cache_key=cache_key)
                if isinstance(result, dict):
                    playlist_name = result['name']
                    is_public = result['is_public']
                    description = result['description']
                else:
                    playlist_name, is_public, description = result 
                    await redis_pool.set(cache_key, json.dumps({"name": playlist_name,
                                                                "user_id": user_id,
                                                                "is_public": is_public,
                                                                "description": description}), ex=1200)

                if preview_url:
                    path = f'songs/'
                    print(playlist_name)
                    filename = os.path.join(path, f'{song_name}.mp3')
                    print(os.path.exists(filename))
                    if not os.path.exists(filename):
                        await download_preview(preview_url, filename)

                    await cursor.execute(f'''INSERT INTO songs VALUES('{song_id}', "{song_name}", {playlist_id})''')
                    await conn.commit()
                    cache_key = f'song:{spotify_url}'
                    await redis_pool.set(cache_key, json.dumps({"name": song_name, "id": song_id}), ex=1200)
                    await redis_pool.set(f'song:{song_id}', json.dumps({"name": song_name}), ex=1200)

                    await cursor.execute(f"SELECT COUNT(name) FROM songs WHERE playlist_id={playlist_id}")
                    n_songs = (await cursor.fetchone())[0]
                    print(is_public)
                    if n_songs == 4 and is_public:
                        await search.add_playlist(id=playlist_id, name=playlist_name, username=username, description=description)
                    if n_songs == 1:
                        await vector_search.insert(playlist_name, user_id, song_name, is_public)
                    else:
                        await vector_search.update_add_song(playlist_name, user_id, song_name)
                    await bot.send_message(user_id, f'Song with name {song_name} has been added to playlist {playlist_name}.',
                                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                                        InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
                    cur_playlists.pop(message.from_user.id)
                    await state.clear()
                else:
                    await bot.send_message(user_id, text='Preview not available for this track. Please provide a valid Spotify song ID.',
                                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                                        InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    except TypeError:
        await bot.send_message(user_id, "The link of this song is invalid. Please provide a valid song link:",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                            InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    except aiomysql.IntegrityError:
        await bot.send_message(user_id, text="The song is already in the playlist. Please provide a song which is not present in the playlist:",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                            InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))

@router_delete_song.callback_query(F.data=='delete_song')
async def delete_song(callback: CallbackQuery, state):
    username = callback.from_user.username
    user_id = callback.from_user.id
    logger.info("CHOOSE PLAYLIST", extra={'user': username})
    
    cache_key = f'user:{user_id}'
    result = await retrieve_data(sql_query=f"SELECT id, name FROM playlists WHERE user_id='{callback.from_user.id}'",
                                 cache_key=cache_key)
    if isinstance(result, dict):
        playlists_ids, playlists_names = list(zip(*result['playlists']))
    elif isinstance(result, list):
        playlists_ids, playlists_names = result
        await redis_pool.set(cache_key, json.dumps({"playlists": list(zip(playlists_ids, playlists_names)),
                                                    "username": username}), ex=1200)
    else:
        playlists_ids = []
    if not playlists_ids:
        await bot.send_message(user_id, text="You don't have any playlists in your library, so you can't delete anything. \
                               Please create a playlist to interact with it.",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                            InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
        return 
    await bot.send_message(user_id, text=f'Choose the playlist from your library to delete a song:', 
                           reply_markup=(await inline_lists(playlists_names, playlists_ids, "playlist_list_delete_song")))

@router_delete_song.callback_query(F.data.endswith(' playlist_list_delete_song'))
async def playlist_list_delete(callback, state):
    username = callback.from_user.username
    logger.info("CHOOSE SONG", extra={'user': username})
    
    playlist_id = " ".join(callback.data.split()[:-1])

    cache_key = f'playlist_songs:{playlist_id}'
    result = await retrieve_data(sql_query=f"SELECT id, name FROM songs WHERE playlist_id='{playlist_id}'",
                                 cache_key=cache_key)
    if isinstance(result, dict):
        songs_names = result['names']
        songs_ids = result['ids']
    elif isinstance(result, list):
        songs_ids, songs_names = result 
        await redis_pool.set(cache_key, json.dumps({"names": songs_names,
                                                    "ids": songs_ids}), ex=1200)
    else:
        songs_ids = []
    if not songs_ids:
        await bot.send_message(callback.from_user.id, text="You don't have any songs in this playlist",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                            InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
        return

    cur_playlists[callback.from_user.id] = playlist_id

    await bot.send_message(callback.from_user.id, "Please select a song from playlist which you want to delete:", 
                           reply_markup=(await inline_lists(songs_names, songs_ids, "song_list_delete")))

@router_delete_song.callback_query(F.data.endswith(' song_list_delete'))
async def song_list_delete(callback, state):
    username = callback.from_user.username
    logger.info("DELETE SONG", extra={'user': username})
    
    user_id = callback.from_user.id
    song_id = " ".join(callback.data.split()[:-1])
    playlist_id = cur_playlists[user_id]
    cur_playlists.pop(user_id)
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            cache_key = f'song:{song_id}'

            if not await redis_pool.exists(cache_key):
                await cursor.execute(f"SELECT name FROM songs WHERE id='{song_id}' AND playlist_id={playlist_id}")
                song_name = (await cursor.fetchone())[0]
                await redis_pool.set(cache_key, json.dumps({"name": song_name}), ex=1200)
            else:
                json_info = json.loads(await redis_pool.get(cache_key))
                song_name = json_info['name']

            cache_key = f'playlist:{playlist_id}'
            result = await retrieve_data(sql_query=f"SELECT name, is_public, description FROM playlists WHERE id={playlist_id}",
                                 cache_key=cache_key)
            if isinstance(result, dict):
                playlist_name = result['name']
                is_public = result['is_public']
            else:
                playlist_name, is_public, description = result 
                await redis_pool.set(cache_key, json.dumps({"name": playlist_name,
                                                            "user_id": user_id,
                                                            "is_public": is_public,
                                                            "description": description}), ex=1200)
                
            await cursor.execute(f'''DELETE FROM songs WHERE name="{song_name}" AND playlist_id={playlist_id}''')
            await vector_search.update_delete_song(playlist_name, user_id, song_name)
            await conn.commit()

    await bot.send_message(user_id, f"Song {song_name} was deleted successfully.",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))

@router_delete_song.callback_query(F.data=='delete_playlist')
async def ask_for_song_id(callback: CallbackQuery, state):
    username = callback.from_user.username
    user_id = callback.from_user.id
    logger.info("CHOOSE PLAYLIST DELETE", extra={'user': username})
    cache_key = f'user:{user_id}'
    result = await retrieve_data(sql_query=f"SELECT id, name FROM playlists WHERE user_id='{callback.from_user.id}'",
                                 cache_key=cache_key)
    if isinstance(result, dict):
        playlists_ids, playlists_names = list(zip(*result['playlists']))
    elif isinstance(result, list):
        playlists_ids, playlists_names = result
    else:
        playlists_ids = []
    if not playlists_ids:
        await bot.send_message(user_id, text="You don't have any playlists in your library, so you can't delete anything. \
                               Please create a playlist to interact with it.",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                            InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
        return 
    await bot.send_message(user_id, text=f'Choose the playlist from your library to delete it:', 
                           reply_markup=(await inline_lists(playlists_names, playlists_ids, "playlist_list_delete")))

@router_delete_song.callback_query(F.data.endswith(' playlist_list_delete'))
async def ask_for_song_id(callback: CallbackQuery, state):
    username = callback.from_user.username
    logger.info("DELETE PLAYLIST", extra={'user': username})
    
    user_id = callback.from_user.id
    playlist_id = " ".join(callback.data.split()[:-1])
    
    cache_key = f'playlist:{playlist_id}'
    result = await retrieve_data(sql_query=f"SELECT name, is_public, description FROM playlists WHERE id={playlist_id}",
                            cache_key=cache_key)
    if isinstance(result, dict):
        playlist_name = result['name']
        is_public = result['is_public']
    else:
        print(result)
        playlist_name, is_public, description = result 
        await redis_pool.set(cache_key, json.dumps({"name": playlist_name,
                                                    "user_id": user_id,
                                                    "is_public": is_public,
                                                    "description": description}), ex=1200)
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"DELETE FROM playlists WHERE id={playlist_id}")
            await conn.commit()
            await redis_pool.delete(cache_key)
    cache_key = f'user:{user_id}'
    if is_public:
        await search.delete_playlist(id=playlist_id)
    try:
        await vector_search.delete_playlist(playlist_name, user_id)
    except IndexError:
        pass
    await bot.send_message(user_id, f"Playlist {playlist_name} was deleted successfully.",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                        InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    
@router_get.callback_query(F.data=='get_songs')
async def ask_for_playlist_name(callback: CallbackQuery, state):
    username = callback.from_user.username
    user_id = callback.from_user.id
    logger.info("CHOOSE PLAYLIST", extra={'user': username})
    cache_key = f'user:{user_id}'
    result = await retrieve_data(sql_query=f"SELECT id, name FROM playlists WHERE user_id='{callback.from_user.id}'",
                                 cache_key=cache_key)
    if isinstance(result, dict):
        playlists_ids, playlists_names = list(zip(*result['playlists']))
    elif isinstance(result, list):
        playlists_ids, playlists_names = result
        await redis_pool.set(cache_key, json.dumps({"playlists": list(zip(playlists_ids, playlists_names)),
                                                    "username": username}), ex=1200)
    else:
        playlists_ids = []
    if not playlists_ids:
        await bot.send_message(user_id, text="You don't have any playlists in library. Please create a one to start adding songs to it.",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                        InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
        return
    await bot.send_message(user_id, "Choose the playlist:", 
                           reply_markup=(await inline_lists(playlists_names, playlists_ids, 'get_songs_pl_chosen')))

@router_get.callback_query(F.data.endswith(' get_songs_pl_chosen'))
async def get_songs(callback: CallbackQuery, state):
    user_id = callback.from_user.id
    username = callback.from_user.username
    logger.info("GET SONGS", extra={'user': username})
    
    playlist_id = " ".join(callback.data.split()[:-1])
    cache_key = f'playlist_songs:{playlist_id}'
    result = await retrieve_data(sql_query=f"SELECT id, name FROM songs WHERE playlist_id='{playlist_id}'",
                                 cache_key=cache_key)
    if isinstance(result, dict):
        songs_names = result['names']
    elif isinstance(result, list):
        songs_ids, songs_names = result 
        await redis_pool.set(cache_key, json.dumps({"names": songs_names,
                                                    "ids": songs_ids}), ex=1200)
    else:
        songs_ids = []
    if not songs_ids:
        await bot.send_message(user_id, text="This playlist is empty. Please add some songs to interact with them.",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                            InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
        return
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SELECT name FROM songs WHERE playlist_id='{playlist_id}'")
            songs_names = await cursor.fetchall()
            cache_key = f'playlist:{playlist_id}'
            result = await retrieve_data(sql_query=f"SELECT name FROM playlists WHERE id='{playlist_id}'",
                                         cache_key=cache_key)
            if isinstance(result, dict):
                playlist_name = result['name']
            elif isinstance(result, list):
                playlist_name = result 
    
    reply = f"Here are your songs from {playlist_name} playlist:\n"
    for i, song in enumerate(songs_names):
        reply += f"{i + 1}. " + song[0] + "\n"
    await bot.send_message(user_id, reply,
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))


@router_quiz.callback_query(F.data.endswith(' quiz_amount'))
async def amount_quiz(callback: CallbackQuery, state):
    username = callback.from_user.username
    user_id = callback.from_user.id
    logger.info("QUESTIONS AMOUNT", extra={'user': username})
    quiz_type[user_id] = callback.data.split()[0]
    user_id = callback.from_user.id
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await state.set_state(Form.got_amount)
            await cursor.execute(f'''SELECT MAX(cnt) FROM (SELECT COUNT(name) as cnt FROM songs 
                                WHERE playlist_id in (SELECT id FROM playlists WHERE user_id = {user_id})
                                GROUP BY playlist_id) as counts''')
            max_amount[user_id] = (await cursor.fetchone())[0] 
    if not max_amount[user_id] or max_amount[user_id] < 4:
        await bot.send_message(user_id, text='''You don't have any playlists with more than 3 songs in your library. You must have minimum 4 songs in order to start a quiz. You can create playlists by clicking "Create new playlist", and adding new songs to the existing one by clicking "Add song".''',
                                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                            InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
        await state.clear()
        return
    if max_amount[user_id] < 1:
        raise ValueError
    await bot.send_message(user_id, f"Enter the amount of questions(less than or equal {max_amount[user_id]}):",
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                            InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))

@router_quiz.message(Form.got_amount)
async def pl_quiz(message, state):
    username = message.from_user.username
    logger.info("CHOOSE PLAYLIST", extra={'user': username})
    user_id = message.from_user.id
    try:
        
        questions_left[user_id] = int(message.text)
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"SELECT id FROM playlists WHERE user_id='{user_id}'")
                playlists_ids = await cursor.fetchall()
                new_ids = []
                for playlist_id in playlists_ids:
                    await cursor.execute(f"SELECT name FROM songs WHERE playlist_id={playlist_id[0]}")
                    songs = await cursor.fetchall()
                    if len(songs) >= questions_left[user_id] and len(songs) >= 4:
                        new_ids.append(playlist_id[0])
                if not new_ids:
                    raise ValueError
                print(new_ids)
                max_points[user_id] = questions_left[user_id]
                points[user_id] = 0
                playlists_names = []
                for id in new_ids:
                    await cursor.execute(f"SELECT name FROM playlists WHERE id = {id}")
                    playlists_names.append(await cursor.fetchone())
        new_ids = [(id, ) for id in new_ids]
        print(new_ids)
        await bot.send_message(user_id, "Choose the playlist for a quiz:", 
                            reply_markup=(await inline_lists(playlists_names, new_ids, 'quiz')))
        await state.clear()
    except ValueError:
        await bot.send_message(user_id, f"None of your playlists contain such a large amount of songs. Please enter the number less than {max_amount[user_id]}:")

    
@router_quiz.callback_query(F.data.endswith(' quiz'))
async def quiz(callback: CallbackQuery, state):
    user_id = callback.from_user.id
    username = callback.from_user.username
    if callback.data.split()[0] in ['melody', 'facts']:
        quiz_type[user_id] = callback.data.split()[0]
    print(questions_left, max_points, cur_playlists, songs_left)
    if correct_options_dict.get(user_id):
        if correct_options_dict[user_id][0] == " ".join(callback.data.split()[:-1]):
            points[user_id] += 1
            await bot.send_message(user_id, "Correct!")
        else:
            await bot.send_message(user_id, f"Sorry, but you got it wrong...\nThe correct answer was {correct_options_dict[user_id][1]}")
    questions_left[user_id] -= 1
    
    if not cur_playlists.get(user_id):
        cur_playlists[user_id] = int(" ".join(callback.data.split()[:-1]))
    print(cur_playlists)
    playlist_id = cur_playlists[user_id]
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SELECT name, user_id FROM playlists WHERE id={playlist_id}")
            playlist_name, user_pl_id = (await cursor.fetchone())
            user_path = user_pl_id
            print(user_path)
            if not users_seeds.get(user_id):
                seed = random.randint(1, 1000000)  
                users_seeds[user_id] = seed
            else:
                seed = users_seeds[user_id]
            print(seed)
            random.seed(seed)
            if questions_left[user_id] >= 0:
                
                if not songs_left.get(user_id):
                    await cursor.execute(f"SELECT name FROM songs WHERE playlist_id='{playlist_id}'")
                    songs_names = [name[0] for name in await cursor.fetchall()]
                    songs_all[user_id] = deepcopy(songs_names)
                    random.shuffle(songs_names)
                    print(songs_names)
                else:
                    songs_names = songs_left[user_id]
                correct_option = songs_names.pop()
                songs_left[user_id] = songs_names
                print(quiz_type)
                if (quiz_type.get(user_id) and quiz_type[user_id] == 'melody'):
                    logger.info(f"QUIZ MELODY {questions_left[user_id]}", extra={'user': username})
                    await cursor.execute(f'''SELECT id FROM songs WHERE name="{correct_option}"''')
                    correct_options_dict[user_id] = ((await cursor.fetchone())[0], correct_option)
                    incorrect_options = random.sample([song for song in songs_all[user_id] if song != correct_option], 3)
                    options = [correct_option] + incorrect_options
                    options = [(name, ) for name in options]
                    options_ids = []
                    random.shuffle(options)
                    for i in range(4):
                        await cursor.execute(f'''SELECT id FROM songs WHERE name="{options[i][0]}" AND playlist_id={playlist_id}''')
                        options_ids.append((await cursor.fetchone()))
                    # user_path = user_id if not inviters_info.get(user_id) else inviters_info[user_id]
                    await bot.send_voice(user_id, FSInputFile(f'songs/{user_path}/{playlist_name}/{correct_option}.mp3'), 
                                        caption=f'{max_points[user_id] - questions_left[user_id]}. Choose the correct answer:',
                                        reply_markup=(await inline_lists(options, options_ids, 'quiz')))
                else:
                    logger.info(f"QUIZ FACTS {questions_left[user_id]}", extra={'user': username})
                    info = await rag_genius.retrieve_info(correct_option)
                    description = info['description']
                    lyrics = info['lyrics']
                    prompt = f'''Based on this description and lyrics of the song generate a question for a music quiz in a json format:
                    \nDescription: {description}\nLyrics: {lyrics}
                    '''
                    global counter
                    counter += 1
                    while True:
                        model = 'lmstudio-community/Phi-3.5-mini-instruct-GGUF/Phi-3.5-mini-instruct-Q6_K.gguf'
                        # if counter % 2 == 0:
                        #     model += ':2'
                        question_str = await generate_question(prompt, 'http://localhost:1234/v1/chat/completions', model)
                        print(question_str)
                        start = question_str.find('{')
                        end = question_str.find('}')
                        try:
                            question_dict = json.loads(question_str[start:end+1])
                            print(question_dict)
                            generated_questions[user_id] = question_dict
                            correct_option = question_dict['correct_answer']
                            correct_options_dict[user_id] = ('1', correct_option)
                            options = [[option] for option in question_dict['options']]
                            ids = [['0'], ['0'], ['0'], ['0']]
                            ids[options.index([correct_option])] = ['1']
                            break
                        except:
                            pass
                    await bot.send_message(user_id, question_dict['question'],
                                        reply_markup=(await inline_lists(options, ids, 'quiz')))
                                
            else:
                if not inviters_info.get(user_id):
                    await bot.send_message(user_id, text=f"Congratulations, you've completed the quiz!!! You've got {points[user_id]}/{max_points[user_id]}!\n Don't forget to share your quiz with your friends:",
                                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Share a quiz', callback_data='quiz_share')]]))
                else:
                    await bot.send_message(user_id, text=f"Congratulations, you've completed the quiz!!! You've got {points[user_id]}/{max_points[user_id]}!\n",)
                    inviters_info.pop(user_id)

                await bot.send_message(user_id, text='Would you like to challenge yourself on similar playlists of other users?',
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Yes', 
                                                                                                                callback_data='other_playlist')], 
                                                                        [InlineKeyboardButton(text='No. Back to menu.', 
                                                                                            callback_data='menu')]]))
                songs_left.pop(user_id)
                songs_all.pop(user_id)
                correct_options_dict.pop(user_id)

    
@router_quiz.callback_query(F.data == 'quiz_share')
async def quiz_share(callback: CallbackQuery, state):
    
    user_id = callback.from_user.id
    playlist_id = cur_playlists[user_id]
    token = await generate_unique_token()
    cache_key = f'quiz_share:{token}'
    await redis_pool.set(cache_key, json.dumps({"user_id": user_id, 
                                                "playlist_id": playlist_id,
                                                "max_points":  max_points[user_id],
                                                "quiz_type": quiz_type[user_id],
                                                "seed": users_seeds[user_id]}), ex=1200)

    share_url = f"https://t.me/guess_thee_music_bot?start={token}"
    await bot.send_message(user_id, text=f"Here is your link for the quiz which you can share with your friends:")
    await bot.send_message(user_id, text=share_url, 
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                        InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))

@router_quiz.callback_query(F.data == 'other_playlist')
async def other_playlist(callback: CallbackQuery, state):
    username = callback.from_user.username
    user_id = callback.from_user.id
    logger.info("QUESTIONS AMOUNT OTHER", extra={'user': username})
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f'''SELECT MAX(cnt) FROM (SELECT COUNT(name) as cnt FROM songs WHERE playlist_id IN (SELECT id FROM playlists WHERE is_public = 1 AND user_id <> '{user_id}')
                                GROUP BY playlist_id) as counts''')
            max_amount[user_id] = (await cursor.fetchone())[0] 
    await bot.send_message(user_id, f"Enter the amount of questions(less than or equal {max_amount[user_id]}):",
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                            InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    await state.set_state(Form.other_playlist_got_amount)

@router_quiz.message(Form.other_playlist_got_amount)
async def other_playlist_got_amount(message, state):
    user_id = message.from_user.id
    if message.text.isdigit():
        amount = int(message.text)
    else:
        await bot.send_message(user_id, text='Please enter a valid number:')
        return
    print(max_amount[user_id])
    if amount > max_amount[user_id]:
        await bot.send_message(user_id, text='There are no playlists with this amount of songs. Please enter new amount of songs:')   
    else:
        await state.clear()
        username = message.from_user.username
        logging.info('CHOOSE PLAYLIST OTHER', extra={'user': username})
        playlist_id = cur_playlists[user_id]
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"SELECT name, is_public FROM playlists WHERE id='{playlist_id}'")
                playlist_name, is_public = (await cursor.fetchone())
                offset = None
                if is_public:
                    offset = 1
                objects = (await vector_search.search(f'songs/{user_id}/{playlist_name}', offset=offset, n_questions=int(message.text))).objects
                print(objects)
                playlists_names = []
                playlists_ids = []
                for obj in objects:
                    cur_user_id = obj.properties['user_id']
                    print(type(cur_user_id))
                    await cursor.execute(f"SELECT username FROM users WHERE id='{cur_user_id}'")
                    cur_username = (await cursor.fetchone())[0]
                    cur_playlist_name = obj.properties['name']
                    playlists_names.append((cur_playlist_name + ' by ' + cur_username, ))
                    print(playlists_names)
                    await cursor.execute(f"SELECT id FROM playlists WHERE name='{cur_playlist_name}' AND user_id='{cur_user_id}'")
                    playlists_ids.append(await cursor.fetchone())
        print(playlists_ids)
        cur_playlists.pop(user_id)
        max_points[user_id] = amount
        questions_left[user_id] = max_points[user_id]
        points[user_id] = 0
        await bot.send_message(user_id, text='Choose one of the following playlists', 
                            reply_markup=await inline_lists(playlists_names, playlists_ids, 'quiz'))

async def main():
    global pool
    pool = await aiomysql.create_pool(
                host='localhost',
                user='root',
                password=PASSWORD,
                db='songs'
                )
    await dp.start_polling(bot)

class UserFilter(logging.Filter):
    def filter(self, record):
        
        if not hasattr(record, 'user'):
            record.user = 'system'
        return True
    
if __name__ == '__main__':
    handler = logging.FileHandler('app.log')
    formatter = logging.Formatter("%(asctime)s %(user)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.addFilter(UserFilter())
    logger.info("Started")
    asyncio.run(main())
    logger.info("Finished")
