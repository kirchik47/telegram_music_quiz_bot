from aiogram.types import CallbackQuery, Message
from aiogram import F
from aiogram.fsm.context import FSMContext
import logging
from routers import router_get_songs
from presentation import keyboards as kb
from infrastructure.services.repo_service import RepoService
from app.use_cases.users.user_use_cases import UserUseCases
from app.use_cases.playlists.playlist_use_cases import PlaylistUseCases
from presentation.utils import error_handler


logger = logging.getLogger('handlers')

@router_get_songs.callback_query(F.data=='choose_playlist_get_songs')
@error_handler
async def choose_playlist_get_songs(callback: CallbackQuery, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(callback.from_user.id)
    username = callback.from_user.username

    logger.info("CHOOSE PLAYLIST TO GET SONGS", extra={'user': username})

    sql_user_repo = repo_service.sql_user_repo
    redis_user_repo = repo_service.redis_user_repo
    user_use_cases = UserUseCases(sql_repo=sql_user_repo, redis_repo=redis_user_repo)
    user = await user_use_cases.get(user_id=user_id)
    playlists = user.playlists

    if not playlists:
        await callback.bot.send_message(
            user_id,
            text="You don't have any playlists in your library, so you can't the list of songs. Please create a playlist first.",
            reply_markup=await kb.inline_lists([], [], 'menu')
        )
        return

    playlists_names = [playlist.name for playlist in playlists]
    playlists_ids = [playlist.id for playlist in playlists]

    await callback.bot.send_message(
        user_id,
        text='Choose the playlist from your library to show the list of songs:',
        reply_markup=await kb.inline_lists(playlists_names, playlists_ids, 'choose_song_get')
    )

@router_get_songs.callback_query(F.data.endswith('choose_song_get'))
@error_handler
async def choose_song_get(callback: CallbackQuery, state: FSMContext, repo_service: RepoService, **kwargs):
    playlist_id = callback.data.split()[0]
    user_id = str(callback.from_user.id)
    username = callback.from_user.username

    logger.info("GET SONGS", extra={'user': username})

    sql_playlist_repo = repo_service.sql_playlist_repo
    redis_playlist_repo = repo_service.redis_playlist_repo
    playlist_use_cases = PlaylistUseCases(sql_repo=sql_playlist_repo, redis_repo=redis_playlist_repo)
    
    playlist = await playlist_use_cases.get(playlist_id=playlist_id)
    songs = playlist.songs

    if not songs:
        await callback.bot.send_message(
            user_id,
            text="This playlist doesn't have any songs.",
            reply_markup=await kb.inline_lists([], [], 'menu')
        )
        return

    song_names = [song.title for song in songs]
    reply = f'Here is the list of songs in the {playlist.name} playlist:'
    for i, song_name in enumerate(song_names):
        reply +=  f'\n{i+1}. {song_name}'

    await callback.bot.send_message(
        user_id,
        text=reply,
        reply_markup=await kb.inline_lists([], [], '')

    )