import logging
from presentation.utils import error_handler
import presentation.keyboards as kb 
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from presentation.utils import get_instruction
from aiogram import F
from routers import main_router
from aiogram.types import CallbackQuery


logger = logging.getLogger('handlers')

@main_router.callback_query(F.data == 'instruction')
@error_handler
async def instruction(callback: CallbackQuery, state: FSMContext, **kwargs):
    user_id = str(callback.from_user.id)
    username = callback.from_user.username

    logger.info("INSTRUCTION", extra={'user': username})
    
    instruction = await get_instruction()
    await callback.bot.send_message(
        user_id, 
        text=instruction,
        reply_markup=await kb.inline_lists([], [], ''), # Making inline keyboard only with one button 'Back to menu'
        parse_mode=ParseMode('MarkdownV2') # For bold and italic type font
    )
    