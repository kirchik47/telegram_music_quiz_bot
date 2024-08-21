import aiohttp
import os
from bs4 import BeautifulSoup
import asyncio

GENIUS_CLIENT_ACCESS_TOKEN = os.getenv('GENIUS_CLIENT_ACCESS_TOKEN')

def traverse_tree(cur_tree):
    description = ""
    for child in cur_tree:
        if isinstance(child, dict) and 'children' in child:
            description += traverse_tree(child['children'])
        elif isinstance(child, str):
            description += child
    return description + " " if description.endswith('.') else description

async def retrieve_info(song_name):
    headers = {
            'Authorization': f'Bearer {GENIUS_CLIENT_ACCESS_TOKEN}'
        }
    async with aiohttp.ClientSession() as session:
        url_search = f'https://api.genius.com/search'
        params = {
            'q': song_name
        }
        async with session.get(url_search, headers=headers, params=params) as resp:
            data = await resp.json()
            api_path = data['response']['hits'][0]['result']['api_path']
    async with aiohttp.ClientSession() as session:
        url = f'https://api.genius.com{api_path}'
        async with session.get(url=url, headers=headers) as resp:
            if resp.status != 200:
                print(f"Failed to retrieve song info: {resp.status}")
                return
            info = (await resp.json())['response']['song']
            lyrics_url = "https://genius.com" + info['path']
            print(lyrics_url)
            description = traverse_tree(info['description']['dom']['children'])

        async with session.get(lyrics_url) as lyrics_resp:
            if lyrics_resp.status != 200:
                print(f"Failed to retrieve lyrics: {lyrics_resp.status}")
                return
            bs = BeautifulSoup(await lyrics_resp.text(), 'html.parser')
            lyrics_html = bs.findAll('span', class_='ReferentFragmentdesktop__Highlight-sc-110r0d9-1 jAzSMw')
            lyrics_str = ""
            for lyrics_span in lyrics_html:
                for br in lyrics_span.findAll('br'):
                    br.replace_with('\n')
                lyrics_str += lyrics_span.text + "\n"
            
            print(f"Description:\n{description}\n")
            print(f"Lyrics:\n{lyrics_str}")
    return {'description': description, 'lyrics': lyrics_str}

async def main():
    song_name = 'The Chainsmokers - Something Just Like This' 
    await retrieve_info(song_name)

if __name__ == '__main__':
    asyncio.run(main())
