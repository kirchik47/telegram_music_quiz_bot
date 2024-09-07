from app.domain.repositories_interfaces.user_repo import UserRepoInterface
from app.domain.entities.user import User
from infrastructure.aiomysql_config import MySQLPool


class MySQLUserRepo(UserRepoInterface):
    def __init__(self, pool: MySQLPool):
        self.pool = pool

    async def get(self, user: User) -> User:
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM users WHERE id=%s", (user.id,))
                result = await cursor.fetchone()
                if result:
                    result_dict = {}
                    keys = user.model_fields.keys()
                    for i, key in enumerate(keys):
                        result_dict[key] = result[i]
                    return User.model_validate(result_dict)
                return None

    async def save(self, user: User) -> None:
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO users (id, username) VALUES (%s, %s)",
                    (user.id, user.username)
                )
                await conn.commit()

    async def update(self, user: User) -> None:
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE users SET username=%s WHERE id=%s",
                    (user.username, user.id)
                )
                await conn.commit()

    async def delete(self, user: User) -> None:
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("DELETE FROM users WHERE id=%s", (user.id,))
                await conn.commit()
