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
from aiogram.types import InlineKeyboardButton, CallbackQuery, FSInputFile
import aiomysql
import asyncio
import keyboards as kb


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
cur_playlists = {}
info = {}
questions_left = {}
max_amount = {}
points = {}
max_points = {}
correct_options_dict = {}

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

async def inline_lists(lst, ids, param):
    keyboard = InlineKeyboardBuilder()
    for i, inst in enumerate(lst):
        keyboard.button(text=inst[0], callback_data=f'{ids[i][0]} {param}')
    keyboard = keyboard.adjust(*[1]*len(lst))
    return keyboard.as_markup()


@dp.message(CommandStart())
async def send_welcome(message):
    username = message.from_user.username
    await message.answer(text=f'''Hello {username}! It's a bot for creating music quizes. Do not forget to challenge your friends!''',
                         reply_markup=kb.main)

@dp.message(Form.menu)
async def send_menu(message, state):
    await state.clear()
    await message.answer(text=f'''Choose an option:''',
                         reply_markup=kb.main)
    
@router_add_pl.callback_query(F.data=='create_playlist')
async def ask_for_playlist_name(callback: CallbackQuery, state):
    bot = Bot(token=TG_TOKEN)
    await bot.send_message(callback.from_user.id, "Please provide a name of new playlist:")
    await state.set_state(Form.waiting_for_playlist_name)
    await bot.session.close()

@router_add_pl.message(Form.waiting_for_playlist_name)
async def create_playlist(message, state):
    await state.clear()
    db = await aiomysql.connect(
        host='localhost',
        user='root',
        password=PASSWORD,
        db='songs'
    )
    cursor = await db.cursor()
    await cursor.execute(f"INSERT INTO playlists(name, user_id) VALUES('{message.text}', {message.from_user.id});")
    await db.commit()
    await message.answer(f"Playlist {message.text} was created successfully! Type anything to continue using the bot:")
    await cursor.close()
    db.close()
    await state.set_state(Form.menu)

@router_add_song.callback_query(F.data=='add_song')
async def ask_for_song_id(callback: CallbackQuery, state):
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
    bot = Bot(token=TG_TOKEN)
    await bot.send_message(callback.from_user.id, "Please provide a song link from spotify:")
    await state.set_state(Form.waiting_for_song_id)
    info[callback.from_user.id] = " ".join(callback.data.split()[:-1])
    await bot.session.close()

@router_add_song.message(Form.waiting_for_song_id)
async def add_song_to_playlist(message, state):
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
        playlist_id = info[message.from_user.id]
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
            info.pop(message.from_user.id)
            await message.answer(f'Song with name {song_name} has been added to playlist {playlist_name}. Type anything to continue using the bot:')
            await state.clear()
            await state.set_state(Form.menu)
        else:
            await message.answer('Preview not available for this track. Please provide a valid Spotify song ID.')
        await cursor.close()
        db.close()
    except TypeError:
        await message.answer("The link of this song is invalid. Please provide a valid song link:")
    except:
        await message.answer("The song is already in the playlist. Please provide a song which is not present in the playlist:")

@router_delete_song.callback_query(F.data=='delete_song')
async def ask_for_song_id(callback: CallbackQuery, state):
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
                           reply_markup=(await inline_lists(playlists_names, playlists_ids, "playlist_delete")))
    await bot.session.close()

@router_delete_song.callback_query(F.data.endswith('playlist_delete'))
async def got_playlist_delete(callback, state):
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
    info[callback.from_user.id] = playlist_id
    await cursor.execute(f"SELECT name FROM songs WHERE playlist_id={playlist_id}")
    songs_names = await cursor.fetchall()
    await cursor.execute(f"SELECT id FROM songs WHERE playlist_id={playlist_id}")
    songs_ids = await cursor.fetchall()
    await bot.send_message(callback.from_user.id, "Please select a song from playlist which you want to delete:", 
                           reply_markup=(await inline_lists(songs_names, songs_ids, "song_delete")))
    await cursor.close()
    db.close()
    await bot.session.close()

@router_delete_song.callback_query(F.data.endswith('song_delete'))
async def got_playlist_delete(callback, state):
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
    playlist_id = info[user_id]
    await cursor.execute(f"SELECT name FROM songs WHERE id='{song_id}' AND playlist_id={playlist_id}")
    song_name = (await cursor.fetchone())[0]
    await cursor.execute(f"SELECT name FROM playlists WHERE id={playlist_id}")
    playlist_name = (await cursor.fetchone())[0]
    await cursor.execute(f"DELETE FROM songs WHERE name='{song_name}' AND playlist_id={playlist_id}")
    os.remove(f"songs/{user_id}/{playlist_name}/{song_name}.mp3")
    await db.commit()
    await cursor.close()
    db.close()
    await bot.send_message(user_id, f"Song {song_name} was deleted successfully. Type anything to continue using bot:")
    await state.set_state(Form.menu)
    await bot.session.close()

@router_get.callback_query(F.data=='get_songs')
async def ask_for_playlist_name(callback: CallbackQuery, state):
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
    await bot.send_message(callback.from_user.id, reply + "Type anything to continue using bot:")
    await bot.session.close()
    await state.set_state(Form.menu)

@router_quiz.callback_query(F.data=='quiz')
async def ask_for_pl_quiz(callback: CallbackQuery, state):
    bot = Bot(token=TG_TOKEN)
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
        max_amount[user_id] = (await cursor.fetchone())[0] - 3
        await cursor.close()
        db.close()
        if max_amount[user_id] < 1:
            raise ValueError
        await bot.send_message(user_id, f"Enter the amount of questions(less than {max_amount[user_id]}):")
    except ValueError:
        await bot.send_message(user_id, f"You have no playlists with more than 3 songs. Please add more songs to start quiz. Type anything to continue using bot:")
        await state.clear()
        await state.set_state(Form.menu)
    await bot.session.close()

@router_quiz.message(Form.got_amount)
async def quiz(message, state):
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
            if len(songs) - 4 >= questions_left[user_id]:
                new_ids.append(playlist_id[0])
        if not new_ids:
            await cursor.close()
            db.close()
            raise ValueError
        max_points[user_id] = questions_left[user_id]
        points[user_id] = 0
        ids_str = str(new_ids).replace('[', '(').replace(']', ')')
        await cursor.execute(f"SELECT name FROM playlists WHERE user_id='{user_id}' AND id IN {ids_str}")
        playlists_names = await cursor.fetchall()
        new_ids = [(id, ) for id in new_ids]
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
    bot = Bot(token=TG_TOKEN)
    if correct_options_dict.get(user_id) and correct_options_dict[user_id][0] == " ".join(callback.data.split()[:-1]):
        points[user_id] += 1
        await bot.send_message(user_id, "Correct!")
    elif correct_options_dict.get(user_id):
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
        if not info.get(user_id):
            await cursor.execute(f"SELECT name FROM songs WHERE playlist_id='{playlist_id}'")
            songs_names = [name[0] for name in await cursor.fetchall()]
            random.shuffle(songs_names)
        else:
            songs_names = info[user_id]
        correct_option = songs_names.pop()
        await cursor.execute(f"SELECT id FROM songs WHERE name='{correct_option}'")
        correct_options_dict[user_id] = ((await cursor.fetchone())[0], correct_option)
        info[user_id] = songs_names
        incorrect_options = random.sample(songs_names, 3)
        options = [correct_option] + incorrect_options
        options = [(name, ) for name in options]
        options_ids = []
        random.shuffle(options)
        for i in range(4):
            await cursor.execute(f"SELECT id FROM songs WHERE name='{options[i][0]}' AND playlist_id={playlist_id}")
            options_ids.append((await cursor.fetchone()))
        await bot.send_voice(user_id, FSInputFile(f'songs/{user_id}/{playlist_name}/{correct_option}.mp3'), 
                             caption=f'{max_points[user_id] - questions_left[user_id]}. Choose the correct answer:',
                             reply_markup=(await inline_lists(options, options_ids, 'quiz')))
        await cursor.close()
        db.close()
    else:
        await bot.send_message(user_id, f"Congratulations, you've completed the quiz!!! You've got {points[user_id]}/{max_points[user_id]}!\n Type anything to continue using bot:")
        await state.set_state(Form.menu)
    await bot.session.close()

async def main():
    bot = Bot(token=TG_TOKEN)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())