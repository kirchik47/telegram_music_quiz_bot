from app.domain.repositories_interfaces.user_repo import UserRepoInterface
from app.domain.entities.user import User
from infrastructure.aiomysql_config import MySQLPool
from app.domain.repositories_interfaces.playlist_repo import PlaylistRepoInterface


class MySQLUserRepo(UserRepoInterface):
    def __init__(self, pool: MySQLPool, playlist_repo: PlaylistRepoInterface):
        self.pool = pool
        self.playlist_repo = playlist_repo

    async def get(self, user: User) -> User:
        async with await self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM users WHERE id=%s", (user.id,))
                result = list(await cursor.fetchone())
                result.append(await self.playlist_repo.get_by_user(user))
                if result:
                    result_dict = {}
                    keys = user.model_fields.keys()
                    for i, key in enumerate(keys):
                        result_dict[key] = result[i]
                    print(result_dict)
                    return User.model_validate(result_dict)
                return None

    async def save(self, user: User) -> None:
        async with await self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO users (id, username) VALUES (%s, %s)",
                    (user.id, user.username)
                )
                await conn.commit()

    async def update(self, user: User) -> None:
        async with await self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE users SET username=%s WHERE id=%s",
                    (user.username, user.id)
                )
                await conn.commit()

    async def delete(self, user: User) -> None:
        async with await self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("DELETE FROM users WHERE id=%s", (user.id,))
                await conn.commit()
