from infrastructure.redis_config import RedisPool
from app.domain.repositories_interfaces.quiz_repo import QuizRepoInterface
from app.domain.entities.quiz import Quiz
from app.domain.entities.question import Question
from app.domain.entities.song import Song


class RedisQuizRepo(QuizRepoInterface):
    def __init__(self, redis_pool: RedisPool):
        self.redis_pool = redis_pool
    
    async def get(self, quiz: Quiz) -> Quiz:
        async with await self.redis_pool.get_connection() as conn:
            data = await conn.get(f'quiz:{quiz.id}')
            # If data is present in redis return it as Quiz instance with metadata, otherwise return None
            # and retrieve data from SQL
            if data:
                data = Quiz.model_validate_json(data)
                if data.questions:
                    # Convert the list of questions metadata as dicts to a list of Question objects
                    data.questions = [Question.model_validate(question) for question in data.questions]
                    if data.quiz_type == '0':
                        for question in data.questions:
                            question.options = [Song.model_validate(song) for song in question.options]
                    print(data)
                return data
            return None

    async def save(self, quiz: Quiz) -> None:
        async with await self.redis_pool.get_connection() as conn:
            # Is used both for creating and updating a playlist
            await conn.set(f'quiz:{quiz.id}', quiz.model_dump_json(), ex=3600)

    async def delete(self, quiz: Quiz) -> None:
        async with await self.redis_pool.get_connection() as conn:
            await conn.delete(f'quiz:{quiz.id}')