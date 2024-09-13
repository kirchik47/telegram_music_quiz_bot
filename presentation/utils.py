import requests
import re
import json
from spotipy import Spotify, SpotifyClientCredentials
import os
from redis.asyncio import Redis
import secrets
import aiofiles
import logging
import hashlib
import time
import presentation.keyboards as kb


logger = logging.getLogger('utils')

CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
sp = Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))

# Fetches preview url of the song and its name
async def get_song_preview_url(song_id):
    track_info = sp.track(song_id)
    print(track_info['artists'])
    artists = ", ".join([artist['name'] for artist in track_info['artists']])
    return track_info['preview_url'], artists + " - " + track_info['name']

# Downloads preview to the folder
async def download_preview(url, filename):
    response = requests.get(url)
    async with aiofiles.open(filename, 'wb') as file:
        await file.write(response.content)

# Extracts from spotify url id of the song
async def extract_spotify_track_id(url):
    match = re.search(r'https://open\.spotify\.com/track/([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    else:
        return None

# Generate unique token id for quiz
async def generate_unique_token():
    return secrets.token_hex(32)

# Gets instruction from .txt file
async def get_instruction():
    instruction = ""
    async with aiofiles.open('presentation/instruction.txt', 'r') as f:
        lines = await f.readlines()
        for line in lines:
            instruction += line
    return instruction

# Error handler for cathing errors in different functions
def error_handler(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            obj = args[0]
            user_id = obj.from_user.id
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            await obj.bot.send_message(user_id,
                                       text="Something went wrong. Please try again later.",
                                       reply_markup=await kb.inline_lists([], [], ''))
    return wrapper

async def generate_quiz_id(playlist_name, user_id):
    raw_string = f"{playlist_name}{user_id}" 
    return f"{hashlib.sha256(raw_string.encode()).hexdigest()[:16]}" 

async def generate_playlist_id(playlist_name, user_id):
    raw_string = f"{playlist_name}{user_id}{time.time()}" # Adding current time to generate unique id and prevent collision
    return f"{hashlib.sha256(raw_string.encode()).hexdigest()[:16]}" 
