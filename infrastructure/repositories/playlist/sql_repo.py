from app.domain.repositories_interfaces.playlist_repo import PlaylistRepoInterface
from app.domain.entities.playlist import Playlist
from app.domain.entities.user import User
from infrastructure.aiomysql_config import MySQLPool
from app.domain.repositories_interfaces.song_repo import SongRepoInterface
from aiomysql import IntegrityError


class MySQLPlaylistRepo(PlaylistRepoInterface):
    def __init__(self, pool: MySQLPool, song_repo: SongRepoInterface):
        self.pool = pool
        self.song_repo = song_repo

    async def get(self, playlist: Playlist) -> Playlist:
        async with await self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM playlists WHERE id=%s", (playlist.id, ))
                # Converting to list for appending
                result = list(await cursor.fetchone())
                # Appending songs list with Song instances to the values of fields
                result.append(await self.song_repo.get_by_playlist(playlist))
                if result:
                    # Converting result to dict for assigning its data to Playlist for model validation
                    keys = playlist.model_fields.keys()
                    result_dict = {}
                    for i, key in enumerate(keys):
                        result_dict[key] = result[i]
                    # Setting values for Playlist instance fields
                    return Playlist.model_validate(result_dict)
                return None
    
    async def save(self, playlist: Playlist):
        async with await self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    '''INSERT INTO playlists (id, name, user_id, is_public, description) VALUES (%s, %s, %s, %s, %s)''',
                    (playlist.id, playlist.name, playlist.user_id, playlist.is_public, playlist.description)
                )
                await conn.commit()
                return True

    async def update(self, playlist: Playlist) -> None:
        async with await self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    '''UPDATE playlists SET name=%s, user_id=%s, is_public=%s, description=%s WHERE id=%s''', 
                    (playlist.name, playlist.user_id, playlist.is_public, playlist.description, playlist.id)
                )
                await conn.commit()

    async def delete(self, playlist: Playlist) -> None:
        async with await self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("DELETE FROM playlists WHERE name=%s AND user_id=%s", 
                                     (playlist.name, playlist.user_id))
                await conn.commit()

    async def get_by_user(self, user: User) -> list:
        async with await self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM playlists WHERE user_id=%s", (user.id,))
                result = await cursor.fetchall()
                # Since result is tuple containing tuples with all fields, we need to convert it to list of Playlist instances
                return [Playlist(id=playlist[0],
                                 name=playlist[1],
                                 user_id=playlist[2],
                                 is_public=playlist[3],
                                 description=playlist[4]) for playlist in result]
            