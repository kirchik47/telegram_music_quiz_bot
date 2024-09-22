from app.domain.repositories_interfaces.playlist_repo import PlaylistRepoInterface
from app.domain.entities.playlist import Playlist
from app.domain.entities.song import Song


class PlaylistUseCases:
    def __init__(self, sql_repo: PlaylistRepoInterface, redis_repo: PlaylistRepoInterface):
        self.sql_repo = sql_repo
        self.redis_repo = redis_repo
    
    async def create(self, playlist_id: str, name: str, user_id: str, is_public: bool, description: str) -> bool:
        playlist = Playlist(
            id=playlist_id,
            name=name,
            user_id=user_id,
            is_public=is_public,
            description=description)
        
        # Save playlist in SQL repository
        await self.sql_repo.save(playlist)
        
        # If playlist is saved in SQL repo, save it in Redis cache
        await self.redis_repo.save(playlist)
        
        # Return playlist for future processing in handler
        return playlist

    async def delete(self, playlist_id: str) -> None:
        # Delete playlist from both SQL and Redis repositories
        playlist = Playlist(id=playlist_id)
        await self.sql_repo.delete(playlist)
        await self.redis_repo.delete(playlist)

    async def get(self, playlist_id: str) -> Playlist:
        # Attempt to retrieve the playlist from Redis cache
        playlist = Playlist(id=playlist_id)
        redis_info = await self.redis_repo.get(playlist)
        if redis_info:
            return redis_info
        
        # If not found in Redis, fetch from SQL and update the Redis cache
        playlist = await self.sql_repo.get(playlist)
        await self.redis_repo.save(playlist)
        return playlist
    
    async def update(self, playlist_id: str, name: str, user_id: str, is_public: bool, description: str, songs: list) -> Playlist:
        # Update playlist details including name, description, and list of songs
        playlist = Playlist(
            id=playlist_id,
            name=name,
            user_id=user_id,
            is_public=is_public,
            description=description,
            songs=songs
        )
        
        # Update playlist in SQL repo and refresh the Redis cache with the new data
        await self.sql_repo.update(playlist)
        await self.redis_repo.save(playlist)

        # Returning Playlist instance in case it's needed for further processing in handler
        return playlist

    async def add_song(self, playlist_id: str, song: Song) -> None:
        # Fetch the playlist and append the new song
        playlist = await self.get(playlist_id=playlist_id)
        if playlist.songs:
            playlist.songs.append(song)
        else:
            playlist.songs = [song]
        
        # Update Redis cache with the modified playlist. 
        # We don't need to update SQL repo here because by adding single song, we already assign playlist id to it in db
        await self.redis_repo.save(playlist)

        # Return playlist in case of further processing in handler
        return playlist

    async def delete_song(self, playlist_id: str, song: Song) -> Playlist:
        # Fetch the playlist and remove the song by matching song ID
        playlist = await self.get(playlist_id=playlist_id)
        song_id = song.id
        for song in playlist.songs:
            if song.id == song_id:
                playlist.songs.remove(song)
                break
        
        # Update Redis cache with the modified playlist after the song has been deleted
        await self.redis_repo.save(playlist)
        
        # Return playlist in case of futher processing in handler
        return playlist
