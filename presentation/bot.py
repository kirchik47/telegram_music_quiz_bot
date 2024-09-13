from aiogram import Router
from infrastructure.repositories.user.sql_repo import MySQLUserRepo
from infrastructure.repositories.user.redis_repo import RedisUserRepo
from infrastructure.repositories.playlist.sql_repo import MySQLPlaylistRepo
from infrastructure.repositories.playlist.redis_repo import RedisPlaylistRepo
from infrastructure.repositories.song.sql_repo import MySQLSongRepo
from infrastructure.repositories.song.redis_repo import RedisSongRepo
from infrastructure.repositories.quiz.redis_repo import RedisQuizRepo
from infrastructure.aiomysql_config import MySQLPool
from infrastructure.redis_config import RedisPool
from config.main_config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT, REDIS_HOST, REDIS_PORT
from middlewares.repo_middleware import RepoMiddleware
from infrastructure.services.repo_service import RepoService
from routers import (main_router, router_add_song, router_create_playlist, router_delete_song, 
                     router_delete_playlist, router_quiz, router_get, router_search, router_edit)

from aiogram import Bot, Dispatcher
from config.main_config import TG_TOKEN
import asyncio
from config import logging_config # Importing config to apply it
import handlers # Importing handlers module to register them in dispatcher


bot = Bot(TG_TOKEN)
dp = Dispatcher()

async def main():
    # Creating repo instances and passing them to service for middleware utilization
    sql_pool = MySQLPool(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    redis_pool = RedisPool(host=REDIS_HOST, port=REDIS_PORT, db=0)
    await sql_pool.create_pool()
    await redis_pool.create_pool()
    sql_song_repo = MySQLSongRepo(sql_pool)
    redis_song_repo = RedisSongRepo(redis_pool)

    sql_playlist_repo = MySQLPlaylistRepo(sql_pool, sql_song_repo)
    redis_playlist_repo = RedisPlaylistRepo(redis_pool)

    sql_user_repo = MySQLUserRepo(sql_pool, sql_playlist_repo)
    redis_user_repo = RedisUserRepo(redis_pool)
    

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

    routers = [router_add_song, router_search, router_create_playlist, router_delete_playlist,
            router_delete_song, router_quiz, router_get, router_edit]
    
    main_router.include_routers(*routers)
    
    dp.message.middleware(repo_middleware)
    dp.callback_query.middleware(repo_middleware)
    dp.include_routers(main_router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
  