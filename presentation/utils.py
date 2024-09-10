import requests
import re
import json
from spotipy import Spotify, SpotifyClientCredentials
import os
from redis.asyncio import Redis
import secrets
import aiofiles
import logging


logger = logging.getLogger('utils')

CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
sp = Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))

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

async def generate_unique_token():
    return secrets.token_hex(32)

async def get_instruction():
    instruction = ""
    async with aiofiles.open('presentation/instruction.txt', 'r') as f:
        lines = await f.readlines()
        for line in lines:
            instruction += line
    return instruction

def error_handler(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return "Something went wrong. Please try again later."
    return wrapper
