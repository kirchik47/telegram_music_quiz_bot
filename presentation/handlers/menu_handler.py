import logging
from presentation.messages import MENU_MSG
from presentation.utils import error_handler
import presentation.keyboards as kb 
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram import F
from routers import main_router


logger = logging.getLogger('handlers')

@main_router.callback_query(F.data == 'menu')
@error_handler
async def menu(callback, **kwargs):
    user_id = str(callback.from_user.id)
    username = callback.from_user.username

    logger.info("MENU", extra={'user': username})
    
    await callback.bot.send_message(
        user_id, 
        text=MENU_MSG,
        reply_markup=kb.main,
        parse_mode=ParseMode('MarkdownV2') # For bold and italic type font
    )
    