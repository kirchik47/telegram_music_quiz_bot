from infrastructure.repositories.user.sql_repo import MySQLUserRepo
from infrastructure.repositories.user.redis_repo import RedisUserRepo
from infrastructure.repositories.playlist.sql_repo import MySQLPlaylistRepo
from infrastructure.repositories.playlist.redis_repo import RedisPlaylistRepo
from infrastructure.repositories.song.sql_repo import MySQLSongRepo
from infrastructure.repositories.song.redis_repo import RedisSongRepo
from infrastructure.repositories.quiz.redis_repo import RedisQuizRepo

from aiogram import Bot, Dispatcher, Router
from infrastructure.aiomysql_config import MySQLPool
from infrastructure.redis_config import RedisPool
from config.main_config import TG_TOKEN, DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT, REDIS_HOST, REDIS_PORT
from middlewares.repo_middleware import RepoMiddleware
from infrastructure.services.repo_service import RepoService
import asyncio


bot = Bot(TG_TOKEN)
dp = Dispatcher()
router_add_song = Router()
router_create_playlist = Router()
router_delete_song = Router()
router_delete_playlist = Router()
router_quiz = Router()
router_get = Router()
router_search = Router()
router_edit = Router()

sql_pool = MySQLPool(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
redis_pool = RedisPool(host=REDIS_HOST, port=REDIS_PORT, db=0)

sql_user_repo = MySQLUserRepo(sql_pool)
redis_user_repo = RedisUserRepo(redis_pool)

sql_playlist_repo = MySQLPlaylistRepo(sql_pool)
redis_playlist_repo = RedisPlaylistRepo(redis_pool)

sql_song_repo = MySQLSongRepo(sql_pool)
redis_song_repo = RedisSongRepo(redis_pool)

redis_quiz_repo = RedisQuizRepo(redis_pool)

repo_service = RepoService(
    sql_user_repo=sql_user_repo,
    sql_playlist_repo=sql_playlist_repo,
    sql_song_repo=sql_song_repo,
    redis_user_repo=redis_user_repo,
    redis_playlist_repo=redis_playlist_repo,
    redis_song_repo=redis_song_repo,
    redis_quiz_repo=redis_quiz_repo
    )

repo_middleware = RepoMiddleware(repo_service)
dp.message.middleware(repo_middleware)

dp.include_routers(router_create_playlist, router_edit, router_add_song, router_delete_song, router_delete_playlist,
                     router_quiz, router_get, router_search)


async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
  