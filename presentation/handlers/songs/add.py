from aiogram.types import CallbackQuery, Message
from aiogram import F
from aiogram.fsm.context import FSMContext
import logging
from routers import router_add_song
from presentation import keyboards as kb
from infrastructure.services.repo_service import RepoService
from app.use_cases.users.user_use_cases import UserUseCases
from app.use_cases.playlists.playlist_use_cases import PlaylistUseCases
from app.use_cases.songs.song_use_cases import SongUseCases
from presentation.state_form import Form
from presentation.utils import error_handler
from aiomysql import IntegrityError
from presentation.messages import PREVIEW_NOT_AVAILABLE_MSG, SONG_EXISTS_MSG


logger = logging.getLogger('handlers')

@router_add_song.callback_query(F.data=='choose_playlist_add_song')
@error_handler
async def choose_playlist_add_song(callback: CallbackQuery, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(callback.from_user.id)
    username = callback.from_user.username

    logger.info("CHOOSE PLAYLIST TO ADD SONG", extra={'user': username})

    sql_user_repo = repo_service.sql_user_repo
    redis_user_repo = repo_service.redis_user_repo

    user_use_cases = UserUseCases(sql_repo=sql_user_repo, redis_repo=redis_user_repo)
    user = await user_use_cases.get(user_id)
    playlists = user.playlists
    
    if not playlists:
        await callback.bot.send_message(
            user_id,
            text="You don't have any playlists in your library. Please create one to start adding songs.",
            reply_markup=await kb.inline_lists([], [], 'menu')
        )
        return

    # Prepare playlist names and ids
    playlists_names = [playlist.name for playlist in playlists]
    playlists_ids = [playlist.id for playlist in playlists]

    await callback.bot.send_message(
        user_id,
        text='Choose the playlist from your library to add a song:',
        reply_markup=await kb.inline_lists(playlists_names, playlists_ids, 'add_song_spotify_url')
    )

@router_add_song.callback_query(F.data.endswith(' add_song_spotify_url'))
@error_handler
async def add_song_spotify_url(callback: CallbackQuery, state: FSMContext, **kwargs):
    playlist_id = callback.data.split()[0]
    user_id = str(callback.from_user.id)

    logger.info("PROVIDE SPOTIFY URL", extra={'user': callback.from_user.username})

    await state.update_data(playlist_id=playlist_id)
    
    await callback.bot.send_message(
        user_id,
        "Please provide a song link from Spotify:",
        reply_markup=await kb.inline_lists([], [], 'menu')
    )
    await state.set_state(Form.waiting_for_song_url)

@router_add_song.message(Form.waiting_for_song_url)
@error_handler
async def add_song_to_playlist(message: Message, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(message.from_user.id)
    username = message.from_user.username

    logger.info("ADD SONG TO PLAYLIST", extra={'user': username})

    try:
        playlist_data = await state.get_data()
        playlist_id = playlist_data['playlist_id']

        sql_playlist_repo = repo_service.sql_playlist_repo
        redis_playlist_repo = repo_service.redis_playlist_repo
        
        sql_song_repo = repo_service.sql_song_repo
        redis_song_repo = repo_service.redis_song_repo
        s3_song_repo = repo_service.s3_song_repo
        spotify_service = repo_service.spotify_service

        playlist_use_cases = PlaylistUseCases(sql_repo=sql_playlist_repo, redis_repo=redis_playlist_repo)
        song_use_cases = SongUseCases(sql_repo=sql_song_repo, redis_repo=redis_song_repo, 
                                      s3_repo=s3_song_repo, spotify_service=spotify_service)
        
        song = await song_use_cases.add(url=message.text.strip(), playlist_id=playlist_id)
        if song:
            song_title = song.title

            playlist = await playlist_use_cases.get(playlist_id=playlist_id)
            await playlist_use_cases.add_song(playlist_id, song)
            await message.bot.send_message(
                user_id,
                f'Song "{song_title}" has been added to playlist "{playlist.name}".',
                reply_markup=await kb.inline_lists([], [], 'menu')
            )
            await state.clear()
        else:
            await message.bot.send_message(
                user_id, 
                text=PREVIEW_NOT_AVAILABLE_MSG,
                reply_markup=await kb.inline_lists([], [], ''))
    
    except IntegrityError:
        await message.bot.send_message(
            user_id, 
            text=SONG_EXISTS_MSG)

