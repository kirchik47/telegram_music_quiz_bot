from app.domain.repositories_interfaces.playlist_repo import PlaylistRepoInterface
from app.domain.entities.playlist import Playlist
from app.domain.entities.song import Song


class PlaylistUseCases:
    def __init__(self, sql_repo: PlaylistRepoInterface, redis_repo: PlaylistRepoInterface):
        self.sql_repo = sql_repo
        self.redis_repo = redis_repo
    
    async def create(self, playlist_id: str, name: str, user_id: str, is_public: bool, description: str) -> bool:
        """
        Creates a new playlist and saves it to both SQL and Redis repositories.

        :param playlist_id: The unique identifier for the playlist.
        :param name: The name of the playlist.
        :param user_id: The ID of the user creating the playlist.
        :param is_public: Boolean indicating if the playlist is public.
        :param description: A brief description of the playlist.
        :return: True if the playlist is created successfully.
        """
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
        """
        Deletes a playlist from both SQL and Redis repositories.

        :param playlist_id: The unique identifier of the playlist to delete.
        """
        # Delete playlist from both SQL and Redis repositories
        playlist = Playlist(id=playlist_id)
        await self.sql_repo.delete(playlist)
        await self.redis_repo.delete(playlist)

    async def get(self, playlist_id: str) -> Playlist:
        """
        Retrieves a playlist by its ID. It first checks Redis cache and 
        falls back to SQL if not found.

        :param playlist_id: The unique identifier for the playlist.
        :return: The retrieved Playlist object.
        """
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
        """
        Updates the details of an existing playlist including its name, 
        description, visibility and list of songs.

        :param playlist_id: The unique identifier of the playlist to update.
        :param name: The new name for the playlist.
        :param user_id: The ID of the user who owns the playlist.
        :param is_public: Boolean indicating if the playlist is public.
        :param description: The updated description of the playlist.
        :param songs: The updated list of songs for the playlist.
        :return: The updated Playlist object.
        """
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
        """
        Adds a new song to an existing playlist.

        :param playlist_id: The unique identifier of the playlist to add the song to.
        :param song: The Song object to add to the playlist.
        """
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
        """
        Deletes a song from an existing playlist by matching the song ID.

        :param playlist_id: The unique identifier of the playlist to delete the song from.
        :param song: The Song object to delete from the playlist.
        :return: The updated Playlist object after the song is deleted.
        """
        # Fetch the playlist and remove the song by matching song ID
        playlist = await self.get(playlist_id=playlist_id)
        song_id = song.id
        for song in playlist.songs:
            if song.id == song_id:
                playlist.songs.remove(song)
                break
        
        # Update Redis cache with the modified playlist after the song has been deleted
        await self.redis_repo.save(playlist)
        
        # Return playlist in case of further processing in handler
        return playlist
