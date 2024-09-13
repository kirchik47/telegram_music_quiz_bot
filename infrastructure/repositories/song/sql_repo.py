from app.domain.repositories_interfaces.song_repo import SongRepoInterface
from infrastructure.aiomysql_config import MySQLPool
from app.domain.entities.song import Song
from app.domain.entities.playlist import Playlist


class MySQLSongRepo(SongRepoInterface):
    def __init__(self, pool: MySQLPool):
        self.pool = pool

    async def get(self, song: Song) -> Song:
        async with await self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM songs WHERE id=%s AND playlist_id=%s", (song.id, song.playlist_id))

                result = await cursor.fetchone()
                if result:
                    keys = song.model_fields.keys()
                    result_dict = {}
                    for i, key in enumerate(keys):
                        result_dict[key] = result[i]
                    return Song.model_validate(result_dict)
                return None

    async def save(self, song: Song) -> None:
        async with await self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    '''INSERT INTO songs (id, title, playlist_id) VALUES (%s, %s, %s)''',
                    (song.id, song.title, song.playlist_id)
                )

                await conn.commit()
    
    async def delete(self, song: Song) -> None:
        async with await self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("DELETE FROM songs WHERE id=%s AND playlist_id=%s", 
                                     (song.id, song.playlist_id))
                await conn.commit()
    
    async def get_by_playlist(self, playlist: Playlist) -> tuple:
        async with await self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM songs WHERE playlist_id=%s", (playlist.id,))
                result = await cursor.fetchall()
                print(result)
                return [Song(id=song[0],
                             title=song[1],
                             playlist_id=song[2],
                        ) for song in result]
