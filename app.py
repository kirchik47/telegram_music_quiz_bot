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
from aiogram.types import InlineKeyboardButton, CallbackQuery, FSInputFile, InlineKeyboardMarkup
import aiomysql
import asyncio
import keyboards as kb
import logging
import secrets
from copy import deepcopy
from transformers import LlamaForCausalLM, AutoTokenizer
from openai import OpenAI
import aiohttp
import json


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
dp.include_routers(*[router_add_pl, router_add_song, router_delete_song, router_delete_playlist, router_quiz, router_get])
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

# tokenizer = AutoTokenizer.from_pretrained('meta-llama/Meta-Llama-3.1-8B-Instruct') 
# model = LlamaForCausalLM.from_pretrained('meta-llama/Meta-Llama-3.1-8B-Instruct')

client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")


def get_song_preview_url(song_id):
    track_info = sp.track(song_id)
    return track_info['preview_url'], track_info['album']['artists'][0]['name'] + " - " + track_info['name']

def download_preview(url, filename):
    response = requests.get(url)
    with open(filename, 'wb') as file:
        file.write(response.content)

async def extract_spotify_track_id(url):
    match = re.search(r'https://open\.spotify\.com/track/([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    else:
        return None
    

class Form(StatesGroup):
    waiting_for_song_id = State()
    waiting_for_playlist_name = State()
    menu = State()
    got_amount = State()
    invite_link = State()

async def inline_lists(lst, ids, param, menu=True):
    keyboard = InlineKeyboardBuilder()
    for i, inst in enumerate(lst):
        keyboard.button(text=inst[0], callback_data=f'{ids[i][0]} {param}')
    keyboard.button(text='Back to menu', callback_data='menu')
    keyboard = keyboard.adjust(*[1]*len(lst))
    return keyboard.as_markup()

async def generate_unique_token():
    return secrets.token_hex(32)

async def generate_question(prompt, url, model):
    async with aiohttp.ClientSession() as session:
        payload = {
            'model': model,
            'messages': [{"role": "system", "content": '''You are a bot for creating music quizes you always answer in json output format like {"question": your_generated_question, "options": your_generated_options, "correct_answer": your_generated_correct_answer}'''},
                         {"role": "user", "content": prompt}],
            'temperature': 2,
            'max_tokens': 200, 
            'example_output': {"question": "your_generated_question", 
                               "options": ["your_generated_option1", 
                                           "your_generated_option2",
                                           "your_generated_option3",
                                           "your_generated_option4"],
                                "correct_answer": "your_generated_correct_answer"}
        }
        async with session.post(url, json=payload) as response:
            result = await response.json()
            return result['choices'][0]["message"]['content']


@dp.message(CommandStart())
async def send_welcome(message, state):
    username = message.from_user.username
    args = message.text.split()
    if len(args) > 1:
        db = await aiomysql.connect(
            host='localhost',
            user='root',
            password=PASSWORD,
            db='songs'
        )
        cursor = await db.cursor()
        username = message.from_user.username
        logger.info("QUIZ SHARE", extra={'user': username})

        user_id = message.from_user.id
        token = args[-1]

        await cursor.execute(f"SELECT playlist_id, user_id, quiz_type, max_points FROM quiz_shares WHERE token='{token}'")
        cur_playlists[user_id], inviter_user_id, quiz_type[user_id], max_points[user_id] = (await cursor.fetchone())
        print(max_points)
        inviters_info[user_id] = inviter_user_id
        questions_left[user_id] = max_points[user_id]
        points[user_id] = 0

        await message.answer(text=f"Hello {username}! You've been invited to complete a quiz from your friend! Press the button below to start quiz",
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Start quiz', callback_data=f'quiz')]]))
        
        await cursor.execute(f"DELETE FROM quiz_shares WHERE token='{token}'")
        await db.commit()
        await cursor.close()
        db.close()
    else:
        logger.info("START", extra={'user': username})
        await message.answer(text=f'''Hello {username}! It's a bot for creating music quizes. Do not forget to challenge your friends!''',
                                reply_markup=kb.main)

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
    bot = Bot(token=TG_TOKEN)
    username = message.from_user.username
    logger.info("MENU", extra={'user': username})
    await state.clear()
    await bot.send_message(user_id, text=f'''Choose an option:''',
                         reply_markup=kb.main)
    await bot.session.close()
    
@router_add_pl.callback_query(F.data=='create_playlist')
async def ask_for_playlist_name(callback: CallbackQuery, state):
    username = callback.from_user.username
    logger.info("CREATE PLAYLIST", extra={'user': username})
    bot = Bot(token=TG_TOKEN)
    await bot.send_message(callback.from_user.id, "Please provide a name of new playlist:", 
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    await state.set_state(Form.waiting_for_playlist_name)
    await bot.session.close()

@router_add_pl.message(Form.waiting_for_playlist_name)
async def create_playlist(message, state):
    await state.clear()
    bot = Bot(token=TG_TOKEN)
    cur_playlists[message.from_user.id] = message.text
    await bot.send_message(message.from_user.id, "Will it be public or private playlist?",
                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Public", callback_data='public got_visibility')], 
                                                        [InlineKeyboardButton(text="Private", callback_data='private got_visibility')],
                                                        [InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    await bot.session.close()

@router_add_pl.callback_query(F.data.endswith('got_visibility'))
async def create_playlist(callback, state):
    bot = Bot(token=TG_TOKEN)
    db = await aiomysql.connect(
            host='localhost',
            user='root',
            password=PASSWORD,
            db='songs'
        )
    cursor = await db.cursor()
    visibility = callback.data.split()[0]
    visibility = 1 if visibility == 'public' else 0
    user_id = callback.from_user.id
    playlist_name = cur_playlists[user_id]
    cur_playlists.pop(user_id)
    os.mkdir(f'songs/{user_id}/{playlist_name}')
    await cursor.execute(f"INSERT INTO playlists(name, user_id, is_public) VALUES('{playlist_name}', {user_id}, {visibility});")
    await db.commit()
    await bot.send_message(user_id, text=f"Playlist {playlist_name} was created successfully!",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                        InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    await cursor.close()
    db.close()
    await bot.session.close()

@router_add_song.callback_query(F.data=='add_song')
async def ask_for_song_id(callback: CallbackQuery, state):
    username = callback.from_user.username
    logger.info("CHOOSE PLAYLIST", extra={'user': username})
    db = await aiomysql.connect(
        host='localhost',
        user='root',
        password=PASSWORD,
        db='songs'
    )
    cursor = await db.cursor()
    await cursor.execute(f"SELECT name FROM playlists WHERE user_id='{callback.from_user.id}'")
    playlists_names = await cursor.fetchall()
    await cursor.execute(f"SELECT id FROM playlists WHERE user_id='{callback.from_user.id}'")
    playlists_ids = await cursor.fetchall()
    bot = Bot(token=TG_TOKEN)
    await cursor.close()
    db.close()
    await bot.send_message(callback.from_user.id, text=f'Choose the playlist from your library to add a song:', 
                           reply_markup=(await inline_lists(playlists_names, playlists_ids, "playlist_add")))
    await bot.session.close()

@router_add_song.callback_query(F.data.endswith('playlist_add'))
async def got_playlist(callback, state):
    username = callback.from_user.username
    logger.info("PROVIDE SONG ID", extra={'user': username})
    bot = Bot(token=TG_TOKEN)
    await bot.send_message(callback.from_user.id, "Please provide a song link from spotify:",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    await state.set_state(Form.waiting_for_song_id)
    cur_playlists[callback.from_user.id] = " ".join(callback.data.split()[:-1])
    await bot.session.close()

@router_add_song.message(Form.waiting_for_song_id)
async def add_song_to_playlist(message, state):
    username = message.from_user.username
    logger.info("ADD SONG", extra={'user': username})
    bot = Bot(token=TG_TOKEN)
    try:
        db = await aiomysql.connect(
                host='localhost',
                user='root',
                password=PASSWORD,
                db='songs'
            )
        cursor = await db.cursor()
        song_id = await extract_spotify_track_id(message.text.strip())
        user_id = message.from_user.id
        playlist_id = cur_playlists[message.from_user.id]
        await cursor.execute(f"SELECT name FROM playlists WHERE id={playlist_id} AND user_id='{user_id}'")
        playlist_name = (await cursor.fetchall())[0][0]
        preview_url, song_name = get_song_preview_url(song_id)
        if preview_url:
            user_path = f'songs/{user_id}'
            filepath = f'songs/{user_id}/{playlist_name}'
            if not os.path.exists(user_path):
                os.mkdir(user_path)
            if not os.path.exists(filepath):
                os.mkdir(filepath)
            filename = os.path.join(filepath, f'{song_name}.mp3')
            download_preview(preview_url, filename)
            await cursor.execute(f"INSERT INTO songs VALUES('{song_id}', '{song_name}', {playlist_id})")
            await db.commit()
            cur_playlists.pop(message.from_user.id)
            await bot.send_message(user_id, f'Song with name {song_name} has been added to playlist {playlist_name}.',
                                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                                InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
            await state.clear()
        else:
            await message.answer('Preview not available for this track. Please provide a valid Spotify song ID.')
        await cursor.close()
        db.close()
    except TypeError:
        await message.answer("The link of this song is invalid. Please provide a valid song link:")
    except:
        await message.answer("The song is already in the playlist. Please provide a song which is not present in the playlist:")
    await bot.session.close()

@router_delete_song.callback_query(F.data=='delete_song')
async def delete_song(callback: CallbackQuery, state):
    username = callback.from_user.username
    logger.info("CHOOSE PLAYLIST", extra={'user': username})
    db = await aiomysql.connect(
        host='localhost',
        user='root',
        password=PASSWORD,
        db='songs'
    )
    cursor = await db.cursor()
    await cursor.execute(f"SELECT name FROM playlists WHERE user_id='{callback.from_user.id}'")
    playlists_names = await cursor.fetchall()
    await cursor.execute(f"SELECT id FROM playlists WHERE user_id='{callback.from_user.id}'")
    playlists_ids = await cursor.fetchall()
    bot = Bot(token=TG_TOKEN)
    await cursor.close()
    db.close()
    await bot.send_message(callback.from_user.id, text=f'Choose the playlist from your library to delete a song:', 
                           reply_markup=(await inline_lists(playlists_names, playlists_ids, "playlist_list_delete_song")))
    await bot.session.close()

@router_delete_song.callback_query(F.data.endswith('playlist_list_delete_song'))
async def playlist_list_delete(callback, state):
    username = callback.from_user.username
    logger.info("CHOOSE SONG", extra={'user': username})
    bot = Bot(token=TG_TOKEN)
    db = await aiomysql.connect(
        host='localhost',
        user='root',
        password=PASSWORD,
        db='songs'
    )
    cursor = await db.cursor()
    playlist_id = " ".join(callback.data.split()[:-1])
    await cursor.execute(f"SELECT name FROM playlists WHERE id={playlist_id} AND user_id={callback.from_user.id}")
    playlist_name = (await cursor.fetchone())[0]
    cur_playlists[callback.from_user.id] = playlist_id
    await cursor.execute(f"SELECT name FROM songs WHERE playlist_id={playlist_id}")
    songs_names = await cursor.fetchall()
    await cursor.execute(f"SELECT id FROM songs WHERE playlist_id={playlist_id}")
    songs_ids = await cursor.fetchall()
    await bot.send_message(callback.from_user.id, "Please select a song from playlist which you want to delete:", 
                           reply_markup=(await inline_lists(songs_names, songs_ids, "song_list_delete")))
    await cursor.close()
    db.close()
    await bot.session.close()

@router_delete_song.callback_query(F.data.endswith('song_list_delete'))
async def song_list_delete(callback, state):
    username = callback.from_user.username
    logger.info("DELETE SONG", extra={'user': username})
    bot = Bot(token=TG_TOKEN)
    db = await aiomysql.connect(
        host='localhost',
        user='root',
        password=PASSWORD,
        db='songs'
    )
    cursor = await db.cursor()
    user_id = callback.from_user.id
    song_id = " ".join(callback.data.split()[:-1])
    playlist_id = cur_playlists[user_id]
    cur_playlists.pop(user_id)
    await cursor.execute(f"SELECT name FROM songs WHERE id='{song_id}' AND playlist_id={playlist_id}")
    song_name = (await cursor.fetchone())[0]
    await cursor.execute(f"SELECT name FROM playlists WHERE id={playlist_id}")
    playlist_name = (await cursor.fetchone())[0]
    await cursor.execute(f"DELETE FROM songs WHERE name='{song_name}' AND playlist_id={playlist_id}")
    os.remove(f"songs/{user_id}/{playlist_name}/{song_name}.mp3")
    await db.commit()
    await cursor.close()
    db.close()
    await bot.send_message(user_id, f"Song {song_name} was deleted successfully.",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    await bot.session.close()

@router_delete_song.callback_query(F.data=='delete_playlist')
async def ask_for_song_id(callback: CallbackQuery, state):
    username = callback.from_user.username
    logger.info("CHOOSE PLAYLIST DELETE", extra={'user': username})
    db = await aiomysql.connect(
        host='localhost',
        user='root',
        password=PASSWORD,
        db='songs'
    )
    cursor = await db.cursor()
    await cursor.execute(f"SELECT name FROM playlists WHERE user_id='{callback.from_user.id}'")
    playlists_names = await cursor.fetchall()
    await cursor.execute(f"SELECT id FROM playlists WHERE user_id='{callback.from_user.id}'")
    playlists_ids = await cursor.fetchall()
    bot = Bot(token=TG_TOKEN)
    await cursor.close()
    db.close()
    await bot.send_message(callback.from_user.id, text=f'Choose the playlist from your library to delete it:', 
                           reply_markup=(await inline_lists(playlists_names, playlists_ids, "playlist_list_delete")))
    await bot.session.close()

@router_delete_song.callback_query(F.data.endswith('playlist_list_delete'))
async def ask_for_song_id(callback: CallbackQuery, state):
    username = callback.from_user.username
    logger.info("DELETE SONG", extra={'user': username})
    bot = Bot(token=TG_TOKEN)
    db = await aiomysql.connect(
        host='localhost',
        user='root',
        password=PASSWORD,
        db='songs'
    )
    cursor = await db.cursor()
    user_id = callback.from_user.id
    playlist_id = " ".join(callback.data.split()[:-1])

    await cursor.execute(f"SELECT name FROM playlists WHERE id={playlist_id}")
    playlist_name = (await cursor.fetchone())[0]
    await cursor.execute(f"DELETE FROM playlists WHERE id={playlist_id}")
    shutil.rmtree(f"songs/{user_id}/{playlist_name}")
    await db.commit()
    await cursor.close()
    db.close()
    await bot.send_message(user_id, f"Playlist {playlist_name} was deleted successfully.",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                        InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    await bot.session.close()
    
@router_get.callback_query(F.data=='get_songs')
async def ask_for_playlist_name(callback: CallbackQuery, state):
    username = callback.from_user.username
    logger.info("CHOOSE PLAYLIST", extra={'user': username})
    bot = Bot(token=TG_TOKEN)
    db = await aiomysql.connect(
        host='localhost',
        user='root',
        password=PASSWORD,
        db='songs'
    )
    cursor = await db.cursor()
    await cursor.execute(f"SELECT name FROM playlists WHERE user_id='{callback.from_user.id}'")
    playlists_names = await cursor.fetchall()
    await cursor.execute(f"SELECT id FROM playlists WHERE user_id='{callback.from_user.id}'")
    playlists_ids = await cursor.fetchall()
    await bot.send_message(callback.from_user.id, "Choose the playlist:", 
                           reply_markup=(await inline_lists(playlists_names, playlists_ids, 'songs_get')))
    await bot.session.close()

@router_get.callback_query(F.data.endswith('songs_get'))
async def get_songs(callback: CallbackQuery, state):
    username = callback.from_user.username
    logger.info("GET SONGS", extra={'user': username})
    bot = Bot(token=TG_TOKEN)
    db = await aiomysql.connect(
        host='localhost',
        user='root',
        password=PASSWORD,
        db='songs'
    )
    cursor = await db.cursor()
    playlist_id = " ".join(callback.data.split()[:-1])
    await cursor.execute(f"SELECT name FROM songs WHERE playlist_id='{playlist_id}'")
    songs_names = await cursor.fetchall()
    await cursor.execute(f"SELECT name FROM playlists WHERE id='{playlist_id}'")
    playlist_name = (await cursor.fetchone())[0]
    reply = f"Here are your songs from {playlist_name} playlist:\n"
    for i, song in enumerate(songs_names):
        reply += f"{i + 1}. " + song[0] + "\n"
    await cursor.close()
    db.close()
    await bot.send_message(callback.from_user.id, reply,
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    await bot.session.close()

@router_quiz.callback_query(F.data.endswith('quiz_amount'))
async def amount_quiz(callback: CallbackQuery, state):
    username = callback.from_user.username
    user_id = callback.from_user.id
    logger.info("QUESTIONS AMOUNT", extra={'user': username})
    bot = Bot(token=TG_TOKEN)
    quiz_type[user_id] = callback.data.split()[0]
    user_id = callback.from_user.id
    try:
        db = await aiomysql.connect(
                host='localhost',
                user='root',
                password=PASSWORD,
                db='songs'
            )
        cursor = await db.cursor()
        await state.set_state(Form.got_amount)
        await cursor.execute(f'''SELECT MAX(cnt) FROM (SELECT COUNT(name) as cnt FROM songs 
                            WHERE playlist_id in (SELECT id FROM playlists WHERE user_id = {user_id})
                            GROUP BY playlist_id) as counts''')
        max_amount[user_id] = (await cursor.fetchone())[0] 
        await cursor.close()
        db.close()
        if max_amount[user_id] < 1:
            raise ValueError
        await bot.send_message(user_id, f"Enter the amount of questions(less than {max_amount[user_id]}):",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    except ValueError:
        await bot.send_message(user_id, f"You have no playlists with songs. Please add songs to start quiz. Type anything to continue using bot:")
        await state.clear()
    await bot.session.close()

@router_quiz.message(Form.got_amount)
async def pl_quiz(message, state):
    username = message.from_user.username
    logger.info("CHOOSE PLAYLIST", extra={'user': username})
    bot = Bot(token=TG_TOKEN)
    user_id = message.from_user.id
    try:
        db = await aiomysql.connect(
            host='localhost',
            user='root',
            password=PASSWORD,
            db='songs'
        )
        cursor = await db.cursor()
        questions_left[user_id] = int(message.text)
        await cursor.execute(f"SELECT id FROM playlists WHERE user_id='{user_id}'")
        playlists_ids = await cursor.fetchall()
        new_ids = []
        for playlist_id in playlists_ids:
            await cursor.execute(f"SELECT name FROM songs WHERE playlist_id={playlist_id[0]}")
            songs = await cursor.fetchall()
            if len(songs) >= questions_left[user_id] and len(songs) >= 4:
                new_ids.append(playlist_id[0])
        if not new_ids:
            await cursor.close()
            db.close()
            raise ValueError
        print(new_ids)
        max_points[user_id] = questions_left[user_id]
        points[user_id] = 0
        ids_str = str(new_ids).replace('[', '(').replace(']', ')')
        await cursor.execute(f"SELECT name FROM playlists WHERE user_id='{user_id}' AND id IN {ids_str}")
        playlists_names = await cursor.fetchall()
        new_ids = [(id, ) for id in new_ids]
        print(new_ids)
        await bot.send_message(user_id, "Choose the playlist for a quiz:", 
                            reply_markup=(await inline_lists(playlists_names, new_ids, 'quiz')))
        await state.clear()
        await cursor.close()
        db.close()
    except ValueError:
        await bot.send_message(user_id, f"None of your playlists contain such a large amount of songs. Please enter the number less than {max_amount[user_id]}:")
    await bot.session.close()

    
@router_quiz.callback_query(F.data.endswith('quiz'))
async def quiz(callback: CallbackQuery, state):
    user_id = callback.from_user.id
    username = callback.from_user.username
    
    bot = Bot(token=TG_TOKEN)
    if correct_options_dict.get(user_id):
        if correct_options_dict[user_id][0] == " ".join(callback.data.split()[:-1]):
            points[user_id] += 1
            await bot.send_message(user_id, "Correct!")
        else:
            await bot.send_message(user_id, f"Sorry, but you got it wrong...\nThe correct answer was {correct_options_dict[user_id][1]}")
    questions_left[user_id] -= 1
    if questions_left[user_id] >= 0:
        db = await aiomysql.connect(
            host='localhost',
            user='root',
            password=PASSWORD,
            db='songs'
        )
        cursor = await db.cursor()
        if not cur_playlists.get(user_id):
            cur_playlists[user_id] = " ".join(callback.data.split()[:-1])
        playlist_id = cur_playlists[user_id]
        await cursor.execute(f"SELECT name FROM playlists WHERE id='{playlist_id}'")
        playlist_name = (await cursor.fetchone())[0]
        if not songs_left.get(user_id):
            await cursor.execute(f"SELECT name FROM songs WHERE playlist_id='{playlist_id}'")
            songs_names = [name[0] for name in await cursor.fetchall()]
            songs_all[user_id] = deepcopy(songs_names)
            random.shuffle(songs_names)
        else:
            songs_names = songs_left[user_id]
        correct_option = songs_names.pop()
        songs_left[user_id] = songs_names
        print(quiz_type)
        if (quiz_type.get(user_id) and quiz_type[user_id] == 'melody'):
            logger.info(f"QUIZ MELODY {questions_left[user_id]}", extra={'user': username})
            await cursor.execute(f"SELECT id FROM songs WHERE name='{correct_option}'")
            correct_options_dict[user_id] = ((await cursor.fetchone())[0], correct_option)
            incorrect_options = random.sample([song for song in songs_all[user_id] if song != correct_option], 3)
            options = [correct_option] + incorrect_options
            options = [(name, ) for name in options]
            options_ids = []
            random.shuffle(options)
            for i in range(4):
                await cursor.execute(f"SELECT id FROM songs WHERE name='{options[i][0]}' AND playlist_id={playlist_id}")
                options_ids.append((await cursor.fetchone()))
            user_path = user_id if not inviters_info.get(user_id) else inviters_info[user_id]
            await bot.send_voice(user_id, FSInputFile(f'songs/{user_path}/{playlist_name}/{correct_option}.mp3'), 
                                caption=f'{max_points[user_id] - questions_left[user_id]}. Choose the correct answer:',
                                reply_markup=(await inline_lists(options, options_ids, 'quiz')))
        else:
            logger.info(f"QUIZ FACTS {questions_left[user_id]}", extra={'user': username})
            prompt = f"Imagine that you are a creator of the whole music encyclopedia at MusicBrainz. Please provide a not really hard question as for a music quiz with 4 possible choices for this song:\n{correct_option}."
            global counter
            counter += 1
            while True:
                model = 'lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf'
                # if counter % 2 == 0:
                #     model += ':2'
                question_str = await generate_question(prompt, 'http://localhost:1234/v1/chat/completions', model)
                print(question_str)
                start = question_str.find('{')
                end = question_str.find('}')
                try:
                    question_dict = json.loads(question_str[start:end+1])
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
        await cursor.close()
        db.close()
                        

    else:
        if not inviters_info.get(user_id):
            await bot.send_message(user_id, text=f"Congratulations, you've completed the quiz!!! You've got {points[user_id]}/{max_points[user_id]}!\n Don't forget to share your quiz with your friends:",
                                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Share a quiz', callback_data='quiz_share')], 
                                                                                   [InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
        else:
            await bot.send_message(user_id, text=f"Congratulations, you've completed the quiz!!! You've got {points[user_id]}/{max_points[user_id]}!\n",
                                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                                InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
            inviters_info.pop(user_id)
        songs_left.pop(user_id)
        songs_all.pop(user_id)
        correct_options_dict.pop(user_id)
    await bot.session.close()

@router_quiz.callback_query(F.data.endswith('quiz_share'))
async def quiz_share(callback: CallbackQuery, state):
    bot = Bot(token=TG_TOKEN)
    db = await aiomysql.connect(
            host='localhost',
            user='root',
            password=PASSWORD,
            db='songs'
        )
    cursor = await db.cursor()
    user_id = callback.from_user.id
    playlist_id = cur_playlists[user_id]
    token = await generate_unique_token()
    await cursor.execute(f'''INSERT INTO quiz_shares(token, user_id, playlist_id, quiz_type, max_points) 
                           VALUES('{token}', '{user_id}', {playlist_id}, '{quiz_type[user_id]}', {max_points[user_id]})''')
    await db.commit()
    share_url = f"https://t.me/guess_thee_music_bot?start={token}"
    await bot.send_message(user_id, text=f"Here is your link for the quiz which you can share with your friends:")
    await bot.send_message(user_id, text=share_url, 
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                        InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
    await cursor.close()
    await bot.session.close()
    db.close()


async def main():
    bot = Bot(token=TG_TOKEN)
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
