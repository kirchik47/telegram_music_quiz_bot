# infrastructure/repositories/mysql_playlist_repo.py
from app.domain.repositories_interfaces.playlist_repo import PlaylistRepoInterface
from app.domain.entities.playlist import Playlist
from app.domain.entities.user import User
from infrastructure.aiomysql_config import MySQLPool


class MySQLPlaylistRepo(PlaylistRepoInterface):
    def __init__(self, pool: MySQLPool):
        self.pool = pool

    async def get(self, playlist: Playlist) -> Playlist:
        async with await self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM playlists WHERE id=%s", (playlist.id, ))
                result = await cursor.fetchone()
                if result:
                    keys = playlist.model_fields.keys()
                    result_dict = {}
                    for i, key in enumerate(keys):
                        result_dict[key] = result[i]
                    return Playlist.model_validate(result_dict)
                return None

    async def save(self, playlist: Playlist) -> None:
        async with await self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    '''INSERT INTO playlists (name, user_id, is_public, description) VALUES (%s, %s, %s, %s)''',
                    (playlist.name, playlist.user_id, playlist.is_public, playlist.description)
                )

                await conn.commit()

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

    async def get_by_user(self, user: User) -> tuple:
        async with await self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM playlists WHERE user_id=%s", (user.id,))
                result = await cursor.fetchall()
                return result
            