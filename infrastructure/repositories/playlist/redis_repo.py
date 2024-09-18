from infrastructure.redis_config import RedisPool
from app.domain.repositories_interfaces.playlist_repo import PlaylistRepoInterface 
from app.domain.entities.playlist import Playlist
from app.domain.entities.song import Song


class RedisPlaylistRepo(PlaylistRepoInterface):
    def __init__(self, redis_pool: RedisPool):
        self.redis_pool = redis_pool
    
    async def get(self, playlist: Playlist) -> dict:
        async with await self.redis_pool.get_connection() as conn:
            data = await conn.get(f'playlist:{playlist.id}')
            if data:
                data = Playlist.model_validate_json(data)
                if data.songs:
                    data.songs = [Song.model_validate(song) for song in data.songs]
                return data

    async def save(self, playlist: Playlist) -> None:
        async with await self.redis_pool.get_connection() as conn:
            await conn.set(f'playlist:{playlist.id}', playlist.model_dump_json(), ex=3600)

    async def delete(self, playlist: Playlist) -> None:
        async with await self.redis_pool.get_connection() as conn:
            await conn.delete(f'playlist:{playlist.id}')