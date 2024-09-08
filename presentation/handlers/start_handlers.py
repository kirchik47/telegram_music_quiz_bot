import logging
from presentation.messages import START_MSG
from presentation.utils import get_instruction, error_handler
import presentation.keyboards as kb 
from aiogram.enums import ParseMode
from infrastructure.services.repo_service import RepoService
from aiogram.filters import Command, CommandStart
from app.domain.entities.user import User
from routers import main_router


logger = logging.getLogger('handlers')

@main_router.message(CommandStart())
# @error_handler
async def start(message, state, repo_service: RepoService):
    user_id = str(message.from_user.id)
    username = message.from_user.username
    user = User(id=user_id, username=username)
    user_repo = repo_service.sql_user_repo
    if not await user_repo.get(user):
        await user_repo.save(user)
    logger.info("START", extra={'user': username})
    
    instruction = await get_instruction()
    
    await message.bot.send_message(user_id, text=START_MSG.format(username = username) + instruction,
                            reply_markup=kb.main,
                            parse_mode=ParseMode('MarkdownV2'))
    