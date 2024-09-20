from app.domain.repositories_interfaces.playlist_repo import PlaylistRepoInterface
from app.domain.entities.playlist import Playlist
from app.domain.entities.song import Song


class PlaylistUseCases:
    def __init__(self, sql_repo: PlaylistRepoInterface, redis_repo: PlaylistRepoInterface):
        self.sql_repo = sql_repo
        self.redis_repo = redis_repo
    
    async def create(self, playlist_id: str, name: str, user_id: str, is_public: bool, description: str) -> bool:
        playlist = playlist = Playlist(
            id=playlist_id,
            name=name,
            user_id=user_id,
            is_public=is_public,
            description=description)
        
        res = await self.sql_repo.save(playlist)
        if res:
            return res
        await self.redis_repo.save(playlist)

    async def delete(self, playlist_id: str) -> None:
        playlist = Playlist(id=playlist_id)
        await self.sql_repo.delete(playlist)
        await self.redis_repo.delete(playlist)

    async def get(self, playlist_id: str) -> Playlist:
        playlist = Playlist(id=playlist_id)
        # If playlist is in redis, return it from redis, otherwise from sql
        redis_info = await self.redis_repo.get(playlist)
        if redis_info:
            return redis_info
        playlist = await self.sql_repo.get(playlist)
        await self.redis_repo.save(playlist)
        return playlist
    
    async def update(self, playlist_id: str, name: str, user_id: str, is_public: bool, description: str, songs: list) -> None:
        playlist = playlist = Playlist(
            id=playlist_id,
            name=name,
            user_id=user_id,
            is_public=is_public,
            description=description,
            songs=songs
        )
        
        await self.sql_repo.update(playlist)
        await self.redis_repo.save(playlist)

    async def add_song(self, playlist_id: str, song: Song) -> None:
        playlist = await self.get(playlist_id=playlist_id)
        if playlist.songs:
                playlist.songs.append(song)
        else:
            playlist.songs = [song]
        
        # If new song was added to playlist, update redis cache for it
        await self.redis_repo.save(playlist)

    async def delete_song(self, playlist_id: str, song: Song) -> None:
        playlist = await self.get(playlist_id=playlist_id)
        song_id = song.id
        for song in playlist.songs:
            if song.id == song_id:
                playlist.songs.remove(song)
                break
        # If new song was deleted from playlist, update redis cache for it
        await self.redis_repo.save(playlist)
