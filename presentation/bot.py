from aiogram import Bot, Dispatcher, Router
import os
from app.handlers import register_handlers


API_TOKEN = os.getenv("TG_TOKEN")
bot = Bot(API_TOKEN)
dp = Dispatcher()
router_add_song = Router()
router_add_pl = Router()
router_delete_song = Router()
router_delete_playlist = Router()
router_quiz = Router()
router_get = Router()
router_search = Router()
router_edit = Router()
dp.include_routers(router_add_pl, router_edit, router_add_song, router_delete_song, router_delete_playlist,
                     router_quiz, router_get, router_search)
register_handlers(dp)

if __name__ == '__main__':
    dp.start_polling(bot)
  