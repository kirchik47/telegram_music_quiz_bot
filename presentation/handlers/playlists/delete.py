from aiogram.types import CallbackQuery
from aiogram import F
from aiogram.fsm.context import FSMContext
import logging
from routers import router_delete_playlist
from presentation import keyboards as kb
from presentation.utils import error_handler
from infrastructure.services.repo_service import RepoService
from app.domain.entities.user import User
from app.domain.entities.playlist import Playlist
from app.use_cases.users.user_use_cases import UserUseCases
from app.use_cases.playlists.playlist_use_cases import PlaylistUseCases


logger = logging.getLogger('handlers')

@router_delete_playlist.callback_query(F.data == 'choose_playlist_delete')
@error_handler
async def choose_playlist_delete(callback: CallbackQuery, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(callback.from_user.id)
    username = callback.from_user.username

    logger.info("CHOOSE PLAYLIST TO DELETE", extra={'user': username})

    sql_user_repo = repo_service.sql_user_repo
    redis_user_repo =repo_service.redis_user_repo
    user = User(id=user_id)
    user_use_cases = UserUseCases(sql_repo=sql_user_repo, redis_repo=redis_user_repo)
    user = await user_use_cases.get(user)
    playlists = user.playlists
    if not playlists:
        await callback.bot.send_message(
            user_id, 
            text="You don't have any playlists in your library, so you can't delete anything. Please create a playlist to interact with it.",
            reply_markup=await kb.inline_lists([], [], '')
        )
        return

    # Prepare playlist names and ids
    playlists_names = [playlist.name for playlist in playlists]
    playlists_ids = [playlist.id for playlist in playlists]

    await callback.bot.send_message(
        user_id, 
        text='Choose the playlist from your library to delete it:',
        reply_markup=(await kb.inline_lists(playlists_names, playlists_ids, 'delete_playlist')),
    )

@router_delete_playlist.callback_query(F.data.endswith('delete_playlist'))
@error_handler
async def finalize_playlist_deletion(callback: CallbackQuery, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(callback.from_user.id)
    username = callback.from_user.username

    logger.info("DELETING PLAYLIST", extra={'user': username})

    # Extract the playlist ID from the callback data
    playlist_id = callback.data.split()[0]

    # Getting repos from the service from the middleware
    sql_playlist_repo = repo_service.sql_playlist_repo
    redis_playlist_repo = repo_service.redis_playlist_repo
    
    sql_user_repo = repo_service.sql_user_repo
    redis_user_repo = repo_service.redis_user_repo

    user_use_cases = UserUseCases(sql_repo=sql_user_repo, redis_repo=redis_user_repo)
    playlist_use_cases = PlaylistUseCases(sql_repo=sql_playlist_repo, redis_repo=redis_playlist_repo)
    playlist = Playlist(id=playlist_id)
    user = await user_use_cases.get(User(id=user_id))
    # Removing the playlist from cached user playlists

    for playlist in user.playlists:
        if playlist.id == playlist_id:
            user.playlists.remove(playlist)
        break

    # Fetching full info for future weaviate & elastic search integration
    playlist = await playlist_use_cases.get(playlist)

    await playlist_use_cases.delete(playlist)
    # Updating cached playlists
    await user_use_cases.update_playlists(user)

    await callback.bot.send_message(
        user_id,
        text=f"Playlist '{playlist.name}' was deleted successfully.",
        reply_markup=await kb.inline_lists([], [], ''),
    )
