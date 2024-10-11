from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram import F
from aiogram.fsm.context import FSMContext
import logging
from routers import router_quiz
from infrastructure.services.repo_service import RepoService
from app.use_cases.quizzes.melody_quiz_use_cases import QuizUseCases
from app.use_cases.quizzes.facts_quiz_use_cases import FactsQuizUseCases
from app.use_cases.users.user_use_cases import UserUseCases
from app.use_cases.playlists.playlist_use_cases import PlaylistUseCases
from app.use_cases.songs.song_use_cases import SongUseCases
from presentation.state_form import Form
from presentation.utils import error_handler, generate_quiz_id
from presentation.messages import ABSENCE_OF_PLAYLISTS, INSUFFICIENT_SONGS
import presentation.keyboards as kb
from app.domain.entities.question import Question
from app.domain.entities.quiz import Quiz
import time


logger = logging.getLogger('handlers')

@router_quiz.callback_query(F.data.endswith("quiz_choose_playlist"))
@error_handler
async def quiz_choose_playlist(message: Message, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(message.from_user.id)
    logger.info("CHOOSING PLAYLIST FOR QUIZ", extra={'user': message.from_user.username})

    sql_user_repo = repo_service.sql_user_repo
    redis_user_repo = repo_service.redis_user_repo
    user_use_cases = UserUseCases(sql_repo=sql_user_repo, redis_repo=redis_user_repo)

    redis_quiz_repo = repo_service.redis_quiz_repo

    playlists = (await user_use_cases.get(user_id=user_id)).playlists
    
    if not playlists:
        await message.bot.send_message(
            user_id, 
            ABSENCE_OF_PLAYLISTS,
            reply_markup=await kb.inline_lists([], [], ''))
        return
    
    playlists_names = [playlist.name for playlist in playlists]
    playlists_ids = [playlist.id for playlist in playlists]

    await message.bot.send_message(
        user_id,
        "Choose playlist to create a quiz based on it:",
        reply_markup=await kb.inline_lists(playlists_names, playlists_ids, 'quiz_amount')
    )

@router_quiz.callback_query(F.data.endswith('quiz_amount'))
@error_handler
async def quiz_amount(callback: CallbackQuery, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(callback.from_user.id)
    username = callback.from_user.username
    playlist_id = callback.data.split()[0]

    logger.info("ENTERING QUIZ AMOUNT", extra={'user': username})

    sql_playlist_repo = repo_service.sql_playlist_repo
    redis_playlist_repo = repo_service.redis_playlist_repo
    playlist_use_cases = PlaylistUseCases(sql_repo=sql_playlist_repo, redis_repo=redis_playlist_repo)
    playlist = await playlist_use_cases.get(playlist_id=playlist_id)
    songs_amount = len(playlist.songs)
    if songs_amount < 4:
        await callback.bot.send_message(
            user_id,
            text=INSUFFICIENT_SONGS,
            reply_markup=await kb.inline_lists([], [], '')
        )
        await state.clear()
        return
    
    await state.set_state(Form.got_amount)
    await state.update_data(playlist=playlist)
    await callback.bot.send_message(
        user_id,
        f"Enter the amount of questions (max {songs_amount}):",
        reply_markup=await kb.inline_lists([], [], '')
    )


@router_quiz.message(Form.got_amount)
@error_handler
async def quiz_choose_type(message: Message, state: FSMContext, repo_service: RepoService, **kwargs):
    questions_amount = int(message.text)
    await state.update_data(amount=questions_amount)

    user_id = str(message.from_user.id)
    playlist = (await state.get_data())['playlist']
    songs_amount = len(playlist.songs)
    if questions_amount > songs_amount:
        await message.bot.send_message(
            user_id,
            text="Your playlist does not contain such amount of questions.",
            reply_markup=await kb.inline_lists([], [], '')
        )
        return
    
    username = message.from_user.username
    logger.info("CHOOSE TYPE OF QUIZ", extra={'user': username})

    await message.bot.send_message(
        user_id,
        text="Choose type of quiz:",
        reply_markup=await kb.inline_lists(['Guess the song by 30 seconds preview', 
                                            'Guess the song by the fact'], [0, 1], 'quiz')
    )

@router_quiz.callback_query(F.data.endswith('quiz'))
@error_handler
async def start_melody_quiz(callback: CallbackQuery, state: FSMContext, repo_service: RepoService, **kwargs):
    quiz_type = callback.data.split()[0]
    user_id = str(callback.from_user.id)
    data = await state.get_data()
    playlist = data['playlist']
    questions_amount = data['amount']
    
    username = callback.from_user.username
    logger.info("STARTING QUIZ", extra={'user': username})

    redis_quiz_repo = repo_service.redis_quiz_repo
    if  quiz_type == '0':
        logger.debug("QUIZ USE CASES INIT", extra={'user': username})
        quiz_use_cases = QuizUseCases(redis_repo=redis_quiz_repo)
    else:
        aiohttp_service = repo_service.aiohttp_service
        genius_service = repo_service.genius_service
        logger.debug("FACTS QUIZ USE CASES INIT", extra={'user': username})
        quiz_use_cases = FactsQuizUseCases(redis_repo=redis_quiz_repo,
                                           aiohttp_service=aiohttp_service,
                                           genius_service=genius_service)
    logger.debug("QUIZ USE CASES CREATE STARTED", extra={'user': username})
    quiz = await quiz_use_cases.create(
        quiz_id=await generate_quiz_id(playlist_name=playlist.name, user_id=user_id),
        user_id=user_id,
        points=0,
        quiz_type=quiz_type,
        max_points_per_question=60,
        songs=playlist.songs,
        questions_amount=questions_amount
    )
    await state.set_data({'quiz_id': quiz.id,
                          'question_idx': 0})

    logger.debug("QUIZ USE CASES CREATE FINISHED", extra={'user': username})
    
    questions = quiz.questions

    # Send the first question
    question = questions[0]
    await callback.bot.send_message(
        user_id,
        "🎉Quiz Started!🎉"
    )
    if quiz_type == '0':
        await ask_melody_question(callback.bot, user_id, username, quiz, question, repo_service)
    else:
        await ask_facts_question(callback.bot, user_id, username, quiz, question, repo_service)
        
@router_quiz.callback_query(F.data.endswith("quiz_continue"))
@error_handler
async def handle_melody_answer(callback: CallbackQuery, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(callback.from_user.id)
    username = callback.from_user.username
    state_data = await state.get_data()
    quiz_id = state_data['quiz_id']
    question_idx = state_data['question_idx']
    logger.info("HANDLING QUIZ ANSWER", extra={'user': username})

    redis_quiz_repo = repo_service.redis_quiz_repo
    quiz_use_cases = QuizUseCases(redis_repo=redis_quiz_repo)

    quiz = await quiz_use_cases.get(quiz_id=quiz_id)
    question = quiz.questions[question_idx]
    correct_answer_idx = question.correct_answer_index
    if quiz.quiz_type == '0':
        correct_answer = question.options[correct_answer_idx].title
    else:
        correct_answer = question.options[correct_answer_idx]
    points = quiz.points
    # Check user's answer
    if callback.data.split()[0] == '1':
        quiz = await quiz_use_cases.add_points(quiz_id=quiz.id, question_id=question.id)
        points = quiz.points
        await callback.bot.send_message(
            user_id, f"Correct! Your total score is {points}."
        )
    else:
        await callback.bot.send_message(
            user_id, 
            f'''Wrong! The correct answer was {correct_answer}. You've got 0 points for this question😔.\nYour total score is {points}.'''
        )

    # Move to the next question or finish
    if question_idx + 1 < len(quiz.questions):
        await state.update_data({'question_idx': question_idx + 1})
        next_question = quiz.questions[question_idx + 1]
        if quiz.quiz_type == '0':
            await ask_melody_question(callback.bot, user_id, username, quiz, next_question, repo_service)
        else:
            await ask_facts_question(callback.bot, user_id, username, quiz, next_question, repo_service)
    else:
        await callback.bot.send_message(
            user_id, 
            f"Quiz finished! You've got total score of {points}/{quiz.max_points_per_question * len(quiz.questions)} points!🎉🎉🎉",
            reply_markup=await kb.inline_lists([], [], '')
        )
        await quiz_use_cases.delete(quiz.id)
        await state.clear()


async def ask_melody_question(bot, user_id, username, quiz: Quiz, question: Question, repo_service: RepoService):
    options = question.options
    correct_answer_idx = question.correct_answer_index
    correct_answer = options[correct_answer_idx]
    
    sql_song_repo = repo_service.sql_song_repo
    redis_song_repo = repo_service.redis_song_repo
    s3_song_repo = repo_service.s3_song_repo
    spotify_service = repo_service.spotify_service
    song_use_cases = SongUseCases(sql_repo=sql_song_repo, 
                                  redis_repo=redis_song_repo, 
                                  s3_repo=s3_song_repo,
                                  spotify_service=spotify_service)
    song_bytes = await song_use_cases.read_file(correct_answer.title)
    logger.info("SONG FILE READ", extra={'user': username})

    ids = [0] * 4
    ids[correct_answer_idx] = 1
    song_file = BufferedInputFile(song_bytes, filename='song.mp3')
    question.start_time = time.time()
    quiz_use_cases = QuizUseCases(redis_repo=repo_service.redis_quiz_repo)
    await quiz_use_cases.save(quiz_id=quiz.id, 
                              user_id=quiz.user_id,
                              points=quiz.points,
                              quiz_type=quiz.quiz_type,
                              max_points_per_question=quiz.max_points_per_question,
                              questions=quiz.questions)
    # Play song preview (from S3 bucket) for the melody quiz question
    await bot.send_voice(
        user_id, voice=song_file, caption=question.text,
        reply_markup=await kb.inline_lists([options[0].title, 
                                            options[1].title,
                                            options[2].title,
                                            options[3].title], ids, 'quiz_continue')
    )

async def ask_facts_question(bot, user_id, username, quiz: Quiz, question: Question, repo_service: RepoService):
    options = question.options
    correct_answer_idx = question.correct_answer_index
    correct_answer = options[correct_answer_idx]
    ids = [0] * 4
    ids[correct_answer_idx] = 1
    question.start_time = time.time()
    quiz_use_cases = QuizUseCases(redis_repo=repo_service.redis_quiz_repo)
    await quiz_use_cases.save(quiz_id=quiz.id, 
                              user_id=quiz.user_id,
                              points=quiz.points,
                              quiz_type=quiz.quiz_type,
                              max_points_per_question=quiz.max_points_per_question,
                              questions=quiz.questions)
    await bot.send_message(
        user_id,
        text=question.text,
        reply_markup=await kb.inline_lists([options[0], 
                                            options[1],
                                            options[2],
                                            options[3]], ids, 'quiz_continue')
    )
