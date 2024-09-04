# infrastructure/repositories/mysql_playlist_repository.py
from app.domain.repositories_interfaces.playlist_repository import PlaylistRepositoryInterface
from app.domain.entities.playlist import Playlist
from infrastructure.aiomysql_config import MySQLPool
from app.domain.entities.song import Song


class MySQLPlaylistRepository(PlaylistRepositoryInterface):
    def __init__(self, pool: MySQLPool):
        self.pool = pool

    async def get_playlist_by_name(self, user_id: int, name: str) -> Playlist:
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM playlists WHERE user_id=%s AND name=%s", (user_id, name))
                result = await cursor.fetchone()
                if result:
                    playlist = Playlist(name=result['name'])
                    await cursor.execute("SELECT * FROM songs WHERE playlist_id=%s", (result['id'],))
                    songs = await cursor.fetchall()
                    for song in songs:
                        playlist.add_song(Song(title=song['title'], artist=song['artist']))
                    return playlist
                return None

    async def save_playlist(self, user_id: int, playlist: Playlist) -> None:
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO playlists (user_id, name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE name=%s",
                    (user_id, playlist.name, playlist.name)
                )
                playlist_id = conn.insert_id()
                for song in playlist.songs:
                    await cursor.execute(
                        "INSERT INTO songs (playlist_id, title, artist) VALUES (%s, %s, %s)",
                        (playlist_id, song.title, song.artist)
                    )
                await conn.commit()

    async def delete_playlist(self, user_id: int, name: str) -> None:
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("DELETE FROM playlists WHERE user_id=%s AND name=%s", (user_id, name))
                await conn.commit()
