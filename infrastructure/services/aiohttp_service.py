from app.domain.services_interfaces.aiohttp_service import AiohttpServiceInterface
import aiohttp


class AiohttpService(AiohttpServiceInterface):
    def __init__(self, aiohttp_client: aiohttp.ClientSession):
        self.aiohttp_client = aiohttp_client

    async def get(self, url, headers=None, params=None):
        async with self.aiohttp_client.get(url, headers=headers, params=params) as response:
            return await response.json()
    
    async def post(self, url, payload):
        async with self.aiohttp_client.post(url, json=payload) as response:
            return await response.json()

        