from infrastructure.redis_config import RedisPool
from app.domain.repositories_interfaces.song_repo import SongRepoInterface
from app.domain.entities.song import Song


class RedisSongRepo(SongRepoInterface):
    def __init__(self, redis_pool: RedisPool):
        self.redis_pool = redis_pool
    
    async def get(self, song: Song) -> dict:
        async with await self.redis_pool.get_connection() as conn:
            # If data is present in redis return it as Quiz instance with metadata, otherwise return None
            # and retrieve data from SQL
            data = await conn.get(f'song:{song.id}')
            if data:
                return Song.model_validate_json(data)
            return None

    async def save(self, song: Song) -> None:
        async with await self.redis_pool.get_connection() as conn:
            # Is used both for creating and updating a playlist
            await conn.set(f'song:{song.id}', song.model_dump_json(), ex=3600)

    async def delete(self, song: Song) -> None:
        async with await self.redis_pool.get_connection() as conn:
            await conn.delete(f'song:{song.id}')