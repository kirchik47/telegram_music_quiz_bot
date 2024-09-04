import aiomysql
from app.domain.repositories_interfaces.user_repository import UserRepositoryInterface
from app.domain.entities.user import User
from infrastructure.aiomysql_config import MySQLPool


class SQLUserRepository(UserRepositoryInterface):
    def __init__(self, pool: MySQLPool):
        self.pool = pool

    async def get_by_id(self, user_id: int) -> User:
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
                result = await cursor.fetchone()
                if result:
                    result_dict = {}
                    keys = User.to_dict().keys()
                    for i, key in enumerate(keys):
                        result_dict[key] = result[i]
                    return User.from_dict(result_dict['id'], result_dict)
                return None

    async def save(self, user: User) -> None:
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO users (id, username) VALUES (%s, %s)",
                    (user.data['id'], user.data['username'])
                )
                await conn.commit()

    async def update(self, user: User) -> None:
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE users SET username=%s WHERE id=%s",
                    (user.data['username'], user.data['id'])
                )
                await conn.commit()

    async def delete(self, user_id: int) -> None:
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
                await conn.commit()
