import logging
from presentation.messages import START_MSG
from presentation.utils import get_instruction, error_handler
import presentation.keyboards as kb 
from aiogram.enums import ParseMode
from infrastructure.services.repo_service import RepoService
from aiogram.filters import Command, CommandStart
from app.domain.entities.user import User
from routers import main_router
from app.use_cases.users.user_use_cases import UserUseCases


logger = logging.getLogger('handlers')

@main_router.message(CommandStart())
@error_handler
async def start(message, repo_service: RepoService, **kwargs):
    # Get user info
    user_id = str(message.from_user.id)
    username = message.from_user.username

    logger.info("START", extra={'user': username})

    # Create new user instance to save it into db's
    user = User(id=user_id, username=username)
    sql_user_repo = repo_service.sql_user_repo
    redis_user_repo = repo_service.redis_user_repo
    
    user_management_uc = UserUseCases(
        sql_repo=sql_user_repo,
        redis_repo=redis_user_repo
        )
    # It either saves user or does nothing if he is already present there
    await user_management_uc.save_user(user)
    
    instruction = await get_instruction()
    
    await message.bot.send_message(
        user_id, 
        text=START_MSG.format(username = username) + instruction,
        reply_markup=kb.main,
        parse_mode=ParseMode('MarkdownV2') # For bold and italic type font
    )
    