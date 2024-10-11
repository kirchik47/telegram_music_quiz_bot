import aiohttp.client_exceptions
from app.domain.services_interfaces.aiohttp_service import AiohttpServiceInterface
import aiohttp


class AiohttpService(AiohttpServiceInterface):
    def __init__(self):
        self.aiohttp_client = aiohttp.ClientSession()

    async def get(self, url, headers=None, params=None):
        async with self.aiohttp_client.get(url, headers=headers, params=params) as response:
            try:
                return await response.json()
            except aiohttp.client_exceptions.ContentTypeError:
                return response
    
    async def post(self, url, payload):
        async with self.aiohttp_client.post(url, json=payload) as response:
            try:
                return await response.json()
            except aiohttp.client_exceptions.ContentTypeError:
                return response
        