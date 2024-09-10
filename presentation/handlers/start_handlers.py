import logging
from presentation.messages import START_MSG
from presentation.utils import get_instruction, error_handler
import presentation.keyboards as kb 
from aiogram.enums import ParseMode
from infrastructure.services.repo_service import RepoService
from aiogram.filters import Command, CommandStart
from app.domain.entities.user import User
from routers import main_router
from app.use_cases.users.user_management import UserManagementUseCase


logger = logging.getLogger('handlers')

@main_router.message(CommandStart())
@error_handler
async def start(message, state, repo_service: RepoService, **kwargs):
    user_id = str(message.from_user.id)
    username = message.from_user.username

    logger.info("START", extra={'user': username})

    user = User(id=user_id, username=username)
    sql_user_repo = repo_service.sql_user_repo
    redis_user_repo = repo_service.redis_user_repo
    user_db_info = await sql_user_repo.get(user)
    
    user_management_uc = UserManagementUseCase(
        sql_user_repo=sql_user_repo,
        redis_user_repo=redis_user_repo
        )
    await user_management_uc.handle_user(user)
    instruction = await get_instruction()
    
    await message.bot.send_message(
        user_id, 
        text=START_MSG.format(username = username) + instruction,
        reply_markup=kb.main,
        parse_mode=ParseMode('MarkdownV2')
    )
    