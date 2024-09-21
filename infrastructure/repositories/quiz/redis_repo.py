from infrastructure.redis_config import RedisPool
from app.domain.repositories_interfaces.quiz_repo import QuizRepoInterface
from app.domain.entities.quiz import Quiz


class RedisQuizRepo(QuizRepoInterface):
    def __init__(self, redis_pool: RedisPool):
        self.redis_pool = redis_pool
    
    async def get(self, quiz: Quiz) -> dict:
        async with await self.redis_pool.get_connection() as conn:
            data = await conn.get(f'quiz:{quiz.id}')
            # If data is present in redis return it as Quiz instance with metadata, otherwise return None
            # and retrieve data from SQL
            if data:
                return Quiz.model_validate_json(data)
            return None

    async def save(self, quiz: Quiz) -> None:
        async with await self.redis_pool.get_connection() as conn:
            # Is used both for creating and updating a playlist
            await conn.set(f'quiz:{quiz.id}', quiz.model_dump_json(), ex=3600)

    async def delete(self, quiz: Quiz) -> None:
        async with await self.redis_pool.get_connection() as conn:
            await conn.delete(f'quiz:{quiz.id}')