from infrastructure.redis_config import RedisPool
from app.domain.repositories_interfaces.playlist_repo import PlaylistRepoInterface 
from app.domain.entities.playlist import Playlist


class RedisPlaylistRepo(PlaylistRepoInterface):
    def __init__(self, redis_pool: RedisPool):
        self.redis_pool = redis_pool
    
    async def get(self, id: int) -> dict:
        async with self.redis_pool.get_connection() as conn:
            data = await conn.get(f'playlist:{id}')
            if data:
                return Playlist.model_validate_json(data)
            return None

    async def save(self, playlist: Playlist) -> None:
        async with self.redis_pool.get_connection() as conn:
            await conn.set(f'playlist:{playlist.id}', playlist.model_dump_json(), ex=3600)

    async def delete(self, id: int) -> None:
        async with self.redis_pool.get_connection() as conn:
            await conn.delete(f'playlist:{id}')