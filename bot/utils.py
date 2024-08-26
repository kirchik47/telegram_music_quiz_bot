import requests
import re
import json
from spotipy import Spotify, SpotifyClientCredentials
import os
from redis.asyncio import Redis
import secrets


CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
sp = Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))
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

async def retrieve_data(pool, sql_query, cache_key):
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
