from app.domain.repositories_interfaces.playlist_repo import PlaylistRepoInterface
from app.domain.entities.playlist import Playlist


class PlaylistUseCases:
    def __init__(self, sql_repo: PlaylistRepoInterface, redis_repo: PlaylistRepoInterface):
        self.sql_repo = sql_repo
        self.redis_repo = redis_repo
    
    async def create(self, playlist: Playlist) -> bool:
        res = await self.sql_repo.save(playlist)
        if res:
            return res
        await self.redis_repo.save(playlist)

    async def delete(self, playlist: Playlist) -> None:
        await self.sql_repo.delete(playlist)
        await self.redis_repo.delete(playlist)

    async def get(self, playlist: Playlist) -> Playlist:
        # If playlist is in redis, return it from redis, otherwise from sql
        redis_info = await self.redis_repo.get(playlist)
        if redis_info:
            return redis_info
        playlist = await self.sql_repo.get(playlist)
        await self.redis_repo.save(playlist)
        return playlist

    
    async def update(self, playlist: Playlist) -> None:
        await self.sql_repo.update(playlist)
        await self.redis_repo.save(playlist)
