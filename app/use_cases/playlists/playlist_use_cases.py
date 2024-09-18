from app.domain.repositories_interfaces.playlist_repo import PlaylistRepoInterface
from app.domain.entities.playlist import Playlist
from app.domain.entities.song import Song


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

    async def add_song(self, playlist: Playlist, song: Song) -> None:
        if playlist.songs:
                playlist.songs.append(song)
        else:
            playlist.songs = [song]
        
        # If new song was added to playlist, update redis cache for it
        await self.redis_repo.save(playlist)

    async def delete_song(self, playlist: Playlist, song: Song) -> None:
        song_id = song.id
        print(song_id)
        for song in playlist.songs:
            print(song_id, song.id)
            if song.id == song_id:
                print("GOVNO")
                playlist.songs.remove(song)
                break
        print(playlist)
        # If new song was deleted from playlist, update redis cache for it
        await self.redis_repo.save(playlist)
