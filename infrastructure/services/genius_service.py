from app.domain.services_interfaces.aiohttp_service import AiohttpServiceInterface
import os
from bs4 import BeautifulSoup
from config.main_config import GENIUS_CLIENT_ACCESS_TOKEN


def traverse_tree(cur_tree):
    description = ""
    for child in cur_tree:
        if isinstance(child, dict) and 'children' in child:
            description += traverse_tree(child['children'])
        elif isinstance(child, str):
            description += child
    return description + " " if description.endswith('.') else description

class GeniusService:
    def __init__(self, aiohttp_service: AiohttpServiceInterface):
        self.aiohttp_service = aiohttp_service
        self.headers = {
            'Authorization': f'Bearer {GENIUS_CLIENT_ACCESS_TOKEN}'
        }

    async def search_song(self, song_name: str):
        url_search = 'https://api.genius.com/search'
        params = {'q': song_name}
        response = await self.aiohttp_service.get(url=url_search, headers=self.headers, params=params)
        # Return the API path for the first result
        return response['response']['hits'][0]['result']['api_path']

    async def get_song_info(self, api_path: str):
        url = f'https://api.genius.com{api_path}'
        response = await self.aiohttp_service.get(url=url, headers=self.headers)
        song_info = response['response']['song']
        lyrics_url = f"https://genius.com{song_info['path']}"
        description = traverse_tree(song_info['description']['dom']['children'])
        return {'description': description, 'lyrics_url': lyrics_url}

    async def get_lyrics(self, lyrics_url: str):
        lyrics_html = await self.aiohttp_service.get(lyrics_url)
        soup = BeautifulSoup(lyrics_html, 'html.parser')
        lyrics_spans = soup.findAll('span', class_='ReferentFragmentdesktop__Highlight-sc-110r0d9-1 jAzSMw')
        lyrics_str = ""
        for span in lyrics_spans:
            for br in span.findAll('br'):
                br.replace_with('\n')
            lyrics_str += span.text + "\n"
        return lyrics_str

    async def retrieve_info(self, song_name: str):
        try:
            api_path = await self.search_song(song_name)
            song_info = await self.get_song_info(api_path)
            lyrics = await self.get_lyrics(song_info['lyrics_url'])
            return {
                'description': song_info['description'],
                'lyrics': lyrics
            }
        except Exception as e:
            print(f"Error retrieving song info: {e}")
            return None
