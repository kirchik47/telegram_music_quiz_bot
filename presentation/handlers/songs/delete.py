from aiogram.types import CallbackQuery, Message
from aiogram import F
from aiogram.fsm.context import FSMContext
import logging
from routers import router_delete_song
from presentation import keyboards as kb
from infrastructure.services.repo_service import RepoService
from app.domain.entities.user import User
from app.domain.entities.playlist import Playlist
from app.domain.entities.song import Song
from app.use_cases.users.user_use_cases import UserUseCases
from app.use_cases.playlists.playlist_use_cases import PlaylistUseCases
from app.use_cases.songs.song_use_cases import SongUseCases
from presentation.utils import error_handler


logger = logging.getLogger('handlers')

@router_delete_song.callback_query(F.data=='choose_playlist_delete_song')
@error_handler
async def choose_playlist_delete_song(callback: CallbackQuery, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(callback.from_user.id)
    username = callback.from_user.username

    logger.info("CHOOSE PLAYLIST TO DELETE SONG", extra={'user': username})

    sql_user_repo = repo_service.sql_user_repo
    redis_user_repo = repo_service.redis_user_repo
    user = User(id=user_id)
    user_use_cases = UserUseCases(sql_repo=sql_user_repo, redis_repo=redis_user_repo)
    user = await user_use_cases.get(user)
    playlists = user.playlists

    if not playlists:
        await callback.bot.send_message(
            user_id,
            text="You don't have any playlists in your library, so you can't delete any songs. Please create a playlist first.",
            reply_markup=await kb.inline_lists([], [], 'menu')
        )
        return

    playlists_names = [playlist.name for playlist in playlists]
    playlists_ids = [playlist.id for playlist in playlists]

    await callback.bot.send_message(
        user_id,
        text='Choose the playlist from your library to delete a song:',
        reply_markup=await kb.inline_lists(playlists_names, playlists_ids, 'choose_song_delete')
    )

@router_delete_song.callback_query(F.data.endswith('choose_song_delete'))
@error_handler
async def choose_song_delete(callback: CallbackQuery, state: FSMContext, repo_service: RepoService, **kwargs):
    playlist_id = callback.data.split()[0]
    await state.update_data(playlist_id=playlist_id)
    user_id = str(callback.from_user.id)
    username = callback.from_user.username

    logger.info("CHOOSE SONG TO DELETE", extra={'user': username})

    sql_playlist_repo = repo_service.sql_playlist_repo
    redis_playlist_repo = repo_service.redis_playlist_repo
    playlist_use_cases = PlaylistUseCases(sql_repo=sql_playlist_repo, redis_repo=redis_playlist_repo)
    
    playlist = await playlist_use_cases.get(Playlist(id=playlist_id))
    await state.update_data(playlist=playlist)
    songs = playlist.songs

    if not songs:
        await callback.bot.send_message(
            user_id,
            text="This playlist doesn't have any songs to delete.",
            reply_markup=await kb.inline_lists([], [], 'menu')
        )
        return

    song_names = [song.title for song in songs]
    song_ids = [song.id for song in songs]

    await callback.bot.send_message(
        user_id,
        "Please select a song to delete from the playlist:",
        reply_markup=await kb.inline_lists(song_names, song_ids, 'delete_song')
    )

@router_delete_song.callback_query(F.data.endswith('delete_song'))
@error_handler
async def delete_song(callback: CallbackQuery, state: FSMContext, repo_service: RepoService, **kwargs):
    song_id = callback.data.split()[0]
    user_id = str(callback.from_user.id)
    username = callback.from_user.username

    logger.info("DELETE SONG FROM PLAYLIST", extra={'user': username})

    sql_song_repo = repo_service.sql_song_repo
    redis_song_repo = repo_service.redis_song_repo
    s3_song_repo = repo_service.s3_song_repo
    spotify_service = repo_service.spotify_service

    sql_playlist_repo = repo_service.sql_playlist_repo
    redis_playlist_repo = repo_service.redis_playlist_repo

    playlist = (await state.get_data())['playlist']
    playlist_use_cases = PlaylistUseCases(sql_repo=sql_playlist_repo, redis_repo=redis_playlist_repo)
    
    song_use_cases = SongUseCases(sql_repo=sql_song_repo, redis_repo=redis_song_repo,
                                  s3_repo=s3_song_repo, spotify_service=spotify_service)
    song = await song_use_cases.get(Song(id=song_id, playlist_id=(await state.get_data())['playlist_id']))
    await song_use_cases.delete(song) 
    
    await playlist_use_cases.delete_song(playlist, song)
    await callback.bot.send_message(
        user_id,
        f'Song "{song.title}" has been successfully deleted from the playlist.',
        reply_markup=await kb.inline_lists([], [], 'menu')
    )
    await state.clear()
