from app.domain.repositories_interfaces.song_repo import SongRepoInterface
from app.domain.entities.song import Song


class SongUseCases:
    def __init__(self, sql_repo: SongRepoInterface, redis_repo: SongRepoInterface, s3_repo: SongRepoInterface):
        self.sql_repo = sql_repo
        self.redis_repo = redis_repo
        self.s3_repo = s3_repo

    async def add(self, song: Song, url: str) -> bool:
        await self.s3_repo.save(song, url)
        await self.sql_repo.save(song)
        await self.redis_repo.save(song)

    async def delete(self, song: Song) -> None:
        await self.sql_repo.delete(song)
        await self.redis_repo.delete(song)

    async def get(self, song: Song) -> Song:
        # If song is in redis, return it from redis, otherwise from sql
        redis_info = await self.redis_repo.get(song)
        if redis_info:
            return redis_info
        playlist = await self.sql_repo.get(song)
        await self.redis_repo.save(song)
        return playlist
