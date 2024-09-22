from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram import F
from app.use_cases.playlists.playlist_use_cases import PlaylistUseCases
from app.use_cases.users.user_use_cases import UserUseCases
import logging
from routers import router_create_playlist
from presentation.state_form import Form
import presentation.keyboards as kb
from infrastructure.services.repo_service import RepoService
from app.domain.entities.playlist import Playlist
from app.domain.entities.user import User
from presentation.utils import generate_playlist_id, error_handler
from aiomysql import IntegrityError


logger = logging.getLogger('handlers')

@router_create_playlist.callback_query(F.data == 'create_playlist')
@error_handler
async def create_playlist(callback: CallbackQuery, state: FSMContext, **kwargs):
    user_id = str(callback.from_user.id)
    username = callback.from_user.username
    logger.info("CREATE PLAYLIST ENTER NAME", extra={'user': username})

    await callback.bot.send_message(
        user_id, 
        text="Please provide a name for the new playlist:", 
        reply_markup=await kb.inline_lists([], [], ''),
    )
    await state.set_state(Form.waiting_for_playlist_name)


@router_create_playlist.message(Form.waiting_for_playlist_name)
@error_handler
async def wait_for_playlist_name(message: Message, state: FSMContext, **kwargs):
    user_id = str(message.from_user.id)
    username = message.from_user.id

    logger.info("ENTER DESCRIPTION", extra={'user': username})
    
    await state.update_data(playlist_name=message.text)
    await message.bot.send_message(
        user_id,
        text="Please provide a description for your playlist:",
        reply_markup=await kb.inline_lists([], [], '')
    )
    await state.set_state(Form.waiting_for_description)

@router_create_playlist.message(Form.waiting_for_description)
@error_handler
async def wait_for_description(message: Message, state: FSMContext, **kwargs):
    user_id = str(message.from_user.id)
    username = message.from_user.id

    logger.info("SET VISIBILITY", extra={'user': username})

    await state.update_data(description=message.text)
    await message.bot.send_message(
        user_id, 
        text="Will it be a public or private playlist?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                             [InlineKeyboardButton(text="Public", callback_data='public got_visibility')],
                             [InlineKeyboardButton(text="Private", callback_data='private got_visibility')],
                             [InlineKeyboardButton(text='Back to menu', callback_data='menu')]
                         ]),
        )


@router_create_playlist.callback_query(F.data.endswith(' got_visibility'))
@error_handler
async def finalize_playlist_creation(callback: CallbackQuery, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(callback.from_user.id)
    username = callback.from_user.id

    logger.info("PLAYLIST CREATION FINISHED", extra={'user': username})

    data = await state.get_data()
    playlist_name = data['playlist_name']
    description = data['description']
    visibility = 1 if callback.data.endswith('public') else 0

    # Getting repos from the service from the middleware
    sql_playlist_repo = repo_service.sql_playlist_repo
    redis_playlist_repo = repo_service.redis_playlist_repo

    sql_user_repo = repo_service.sql_user_repo
    redis_user_repo = repo_service.redis_user_repo
    # Generating 16 digit hash as playlist id
    playlist_id = await generate_playlist_id(playlist_name, user_id)
    print(playlist_id)
    playlist_use_cases =  PlaylistUseCases(sql_repo=sql_playlist_repo, redis_repo=redis_playlist_repo)

    try:
        await playlist_use_cases.create(
            playlist_id=playlist_id,
            name=playlist_name,
            user_id=user_id,
            is_public=visibility,
            description=description
            )
    except IntegrityError:
        await callback.bot.send_message(
            user_id,
            text='Playlist with this name already exists. Please try creating playlist with different name.',
            reply_markup=await kb.inline_lists([], [], '')
        )
        return
    playlist = await playlist_use_cases.get(playlist_id=playlist_id)
    
    user_use_cases = UserUseCases(sql_repo=sql_user_repo, redis_repo=redis_user_repo)
    user = await user_use_cases.get(user_id=user_id)

    await user_use_cases.add_playlists(user=user, playlist=playlist)
    await state.clear()
    await callback.bot.send_message(
        user_id, 
        text=f"Playlist {playlist_name} was created successfully!",
        reply_markup=await kb.inline_lists([], [], ''),
        )
