from aiogram.types import CallbackQuery, Message
from aiogram import F
from aiogram.fsm.context import FSMContext
import logging
from routers import router_edit_playlist
from presentation import keyboards as kb
from presentation.utils import error_handler
from infrastructure.services.repo_service import RepoService
from app.domain.entities.user import User
from app.domain.entities.playlist import Playlist
from app.use_cases.users.user_use_cases import UserUseCases
from app.use_cases.playlists.playlist_use_cases import PlaylistUseCases
from presentation.state_form import Form


logger = logging.getLogger('handlers')

async def update_playlist(state: FSMContext, repo_service: RepoService, user_id: str):
    playlist_data = await state.get_data()
    playlist_id = playlist_data['id']
    playlist_name = playlist_data['name']
    playlist_description = playlist_data['description']
    visibility = playlist_data['visibility']
    sql_playlist_repo = repo_service.sql_playlist_repo
    redis_playlist_repo = repo_service.redis_playlist_repo
    playlist_use_cases = PlaylistUseCases(sql_repo=sql_playlist_repo, redis_repo=redis_playlist_repo)
    playlist = Playlist(id=playlist_id,
                        name=playlist_name,
                        user_id=user_id,
                        is_public=visibility,
                        description=playlist_description)
    await playlist_use_cases.update(playlist)

@router_edit_playlist.callback_query(F.data == 'choose_playlist_edit')
@error_handler
async def choose_playlist_delete(callback: CallbackQuery, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(callback.from_user.id)
    username = callback.from_user.username

    logger.info("CHOOSE PLAYLIST TO EDIT", extra={'user': username})

    sql_user_repo = repo_service.sql_user_repo
    redis_user_repo =repo_service.redis_user_repo
    user = User(id=user_id)
    user_use_cases = UserUseCases(sql_repo=sql_user_repo, redis_repo=redis_user_repo)
    user = await user_use_cases.get(user)
    playlists = user.playlists
    if not playlists:
        await callback.bot.send_message(
            user_id, 
            text="You don't have any playlists in your library, so you can't edit anything. Please create a playlist to interact with it.",
            reply_markup=await kb.inline_lists([], [], '')
        )
        return

    # Prepare playlist names and ids
    playlists_names = [playlist.name for playlist in playlists]
    playlists_ids = [playlist.id for playlist in playlists]

    await callback.bot.send_message(
        user_id, 
        text='Choose the playlist from your library to edit it:',
        reply_markup=(await kb.inline_lists(playlists_names, playlists_ids, 'edit_playlist_chosen')),
    )

@router_edit_playlist.callback_query(F.data.endswith('edit_playlist_chosen'))
@error_handler
async def edit_playlist_chosen(callback: CallbackQuery, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(callback.from_user.id)
    playlist_id = callback.data.split()[0]
    username = callback.from_user.username

    logger.info("EDIT PLAYLIST CHOOSE OPTION", extra={'user': username})

    sql_playlist_repo = repo_service.sql_playlist_repo
    redis_playlist_repo = repo_service.redis_playlist_repo
    playlist_use_cases = PlaylistUseCases(sql_repo=sql_playlist_repo, redis_repo=redis_playlist_repo)

    playlist = Playlist(id=playlist_id)
    playlist = await playlist_use_cases.get(playlist)
    playlist_name = playlist.name
    playlist_description = playlist.description

    await state.update_data(id=playlist_id, name=playlist_name, description=playlist_description, visibility=playlist.is_public)

    visibility = 'public' if playlist.is_public else 'private'

    await callback.bot.send_message(
        user_id,
        text=f'Name: {playlist_name}\nDescription: {playlist_description}\nVisibility: {visibility}\nChoose an option to edit:',
        reply_markup=await kb.inline_lists(['Change name', 'Change description', 'Change visibility'], 
                                           ['0', '1', '2'], 'edit_playlist_option_chosen')
    )

@router_edit_playlist.callback_query(F.data.endswith('edit_playlist_option_chosen'))
@error_handler
async def edit_playlist_option_chosen(callback: CallbackQuery, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(callback.from_user.id)
    option = int(callback.data.split()[0])

    logger.info("EDIT PLAYLIST OPTION CHOSEN", extra={'user': callback.from_user.username})

    if option == 0:
        await callback.bot.send_message(
            user_id,
            text='Please enter a new name for your playlist:',
            reply_markup=await kb.inline_lists([], [], ''),
        )
        await state.set_state(Form.waiting_for_playlist_name_edit)
    elif option == 1:
        await callback.bot.send_message(
            user_id,
            text='Please enter a new description for your playlist:',
            reply_markup=await kb.inline_lists([], [], ''),
        )
        await state.set_state(Form.waiting_for_playlist_description_edit)
    else:
        logger.info("CHANGE PLAYLIST VISIBILITY", extra={'user': user_id})

        cur_visibility = (await state.get_data())['visibility']
        new_visibility = not cur_visibility
        await state.update_data(visibility=new_visibility)
        await update_playlist(state, repo_service, user_id)

        reply = 'Private' if not new_visibility else 'Public'

        await callback.bot.send_message(
            user_id,
            text=f'The visibility was successfully changed to {reply}.',
            reply_markup=await kb.inline_lists([], [], ''),
        )

@router_edit_playlist.message(Form.waiting_for_playlist_name_edit)
@error_handler
async def update_playlist_name(message: Message, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(message.from_user.id)
    new_name = message.text

    logger.info("CHANGE PLAYLIST NAME", extra={'user': message.from_user.username})

    await state.update_data(name=message.text)
    await update_playlist(state, repo_service, user_id)

    await message.bot.send_message(
        user_id,
        text=f'Playlist name was successfully changed to {new_name}.',
        reply_markup=await kb.inline_lists([], [], ''),
    )
    await state.clear()

@router_edit_playlist.message(Form.waiting_for_playlist_description_edit)
@error_handler
async def update_playlist_name(message: Message, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(message.from_user.id)
    new_name = message.text

    logger.info("CHANGE PLAYLIST DESCRIPTION", extra={'user': message.from_user.username})

    await state.update_data(description=message.text)
    await update_playlist(state, repo_service, user_id)

    await message.bot.send_message(
        user_id,
        text=f'Playlist description was successfully changed to {new_name}.',
        reply_markup=await kb.inline_lists([], [], ''),
    )
    await state.clear()
