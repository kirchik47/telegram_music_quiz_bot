from infrastructure.redis_config import RedisPool
from app.domain.repositories_interfaces.user_repo import UserRepoInterface
from app.domain.entities.user import User


class RedisUserRepo(UserRepoInterface):
    def __init__(self, redis_pool: RedisPool):
        self.redis_pool = redis_pool
    
    async def get(self, user: User) -> dict:
        async with self.redis_pool.get_connection() as conn:
            data = await conn.get(f'user:{user.id}')
            if data:
                return User.model_validate_json(data)
            return None

    async def save(self, user: User) -> None:
        async with self.redis_pool.get_connection() as conn:
            await conn.set(f'user:{user.id}', user.model_dump_json(), ex=3600)

    async def delete(self, user: User) -> None:
        async with self.redis_pool.get_connection() as conn:
            await conn.delete(f'user:{id}')
            