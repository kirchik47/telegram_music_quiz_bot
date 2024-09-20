from aiogram.types import CallbackQuery, Message
from aiogram import F
from aiogram.fsm.context import FSMContext
import logging
from infrastructure.services.repo_service import RepoService
from app.use_cases.quiz.melody_quiz_use_cases import MelodyQuizUseCases
from presentation.state_form import Form
from presentation.utils import error_handler
from presentation.messages import INSUFFICIENT_SONGS_MSG, CHOOSE_PLAYLIST_MSG, QUIZ_STARTED_MSG, QUESTION_MSG

logger = logging.getLogger('handlers')

@router_quiz.callback_query(F.data.endswith('melody_quiz_amount'))
@error_handler
async def melody_quiz_amount(callback: CallbackQuery, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(callback.from_user.id)
    username = callback.from_user.username
    logger.info("CHOOSING MELODY QUIZ AMOUNT", extra={'user': username})

    sql_playlist_repo = repo_service.sql_playlist_repo
    redis_playlist_repo = repo_service.redis_playlist_repo
    melody_quiz_use_cases = MelodyQuizUseCases(sql_repo=sql_playlist_repo, redis_repo=redis_playlist_repo)

    max_amount = await melody_quiz_use_cases.get_max_question_count(user_id)
    if not max_amount or max_amount < 4:
        await callback.bot.send_message(
            user_id,
            text=INSUFFICIENT_SONGS_MSG,
            reply_markup=await kb.inline_lists([], [], 'menu')
        )
        await state.clear()
        return
    
    await state.set_state(Form.got_amount)
    await callback.bot.send_message(
        user_id,
        f"Enter the amount of questions (max {max_amount}):",
        reply_markup=await kb.inline_lists([], [], 'menu')
    )

@router_quiz.message(Form.got_amount)
@error_handler
async def melody_quiz_playlist(message: Message, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(message.from_user.id)
    logger.info("CHOOSING PLAYLIST FOR MELODY QUIZ", extra={'user': message.from_user.username})

    sql_playlist_repo = repo_service.sql_playlist_repo
    redis_playlist_repo = repo_service.redis_playlist_repo
    melody_quiz_use_cases = MelodyQuizUseCases(sql_repo=sql_playlist_repo, redis_repo=redis_playlist_repo)

    try:
        questions_amount = int(message.text)
        playlists = await melody_quiz_use_cases.get_eligible_playlists(user_id, questions_amount)
        
        if not playlists:
            raise ValueError("No playlists with enough songs")
        
        playlists_names = [playlist.name for playlist in playlists]
        playlists_ids = [playlist.id for playlist in playlists]

        await message.bot.send_message(
            user_id,
            CHOOSE_PLAYLIST_MSG,
            reply_markup=await kb.inline_lists(playlists_names, playlists_ids, 'melody_quiz_start')
        )
        await state.update_data(questions_amount=questions_amount)
        await state.clear()
    except ValueError:
        await message.bot.send_message(
            user_id, f"None of your playlists have enough songs. Enter a number less than {questions_amount}:"
        )

@router_quiz.callback_query(F.data.endswith('melody_quiz_start'))
@error_handler
async def start_melody_quiz(callback: CallbackQuery, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(callback.from_user.id)
    username = callback.from_user.username
    logger.info("STARTING MELODY QUIZ", extra={'user': username})

    data = await state.get_data()
    questions_amount = data['questions_amount']
    playlist_id = callback.data.split()[0]

    sql_playlist_repo = repo_service.sql_playlist_repo
    redis_playlist_repo = repo_service.redis_playlist_repo
    s3_song_repo = repo_service.s3_song_repo

    melody_quiz_use_cases = MelodyQuizUseCases(sql_repo=sql_playlist_repo, redis_repo=redis_playlist_repo, s3_repo=s3_song_repo)

    # Generate the quiz questions (select songs and shuffle for quiz)
    quiz_questions = await melody_quiz_use_cases.generate_quiz(playlist_id, questions_amount)
    await melody_quiz_use_cases.save_quiz_state(user_id, quiz_questions)

    # Send the first question
    question = quiz_questions[0]
    await callback.bot.send_message(
        user_id,
        QUIZ_STARTED_MSG,
        reply_markup=await kb.inline_lists([], [], 'menu')
    )
    
    await ask_melody_question(callback.bot, user_id, question, 1, questions_amount)
    await state.set_state(Form.waiting_for_melody_answer)

@router_quiz.message(Form.waiting_for_melody_answer)
@error_handler
async def handle_melody_answer(message: Message, state: FSMContext, repo_service: RepoService, **kwargs):
    user_id = str(message.from_user.id)
    username = message.from_user.username
    logger.info("HANDLING MELODY QUIZ ANSWER", extra={'user': username})

    melody_quiz_use_cases = MelodyQuizUseCases(redis_repo=repo_service.redis_playlist_repo)

    # Retrieve quiz state
    quiz_data = await melody_quiz_use_cases.get_quiz_state(user_id)
    current_question = quiz_data['current_question']
    correct_answer = current_question['correct_answer']

    # Check user's answer
    if message.text.lower() == correct_answer.lower():
        await message.bot.send_message(
            user_id, "Correct! 🎉"
        )
    else:
        await message.bot.send_message(
            user_id, f"Wrong! The correct answer was {correct_answer}. 😔"
        )

    # Move to the next question or finish
    quiz_data['current_question_index'] += 1
    if quiz_data['current_question_index'] < len(quiz_data['questions']):
        next_question = quiz_data['questions'][quiz_data['current_question_index']]
        await ask_melody_question(message.bot, user_id, next_question, quiz_data['current_question_index'] + 1, len(quiz_data['questions']))
        await melody_quiz_use_cases.save_quiz_state(user_id, quiz_data)
    else:
        await message.bot.send_message(
            user_id, "Quiz finished! 🎉"
        )
        await melody_quiz_use_cases.delete_quiz_state(user_id)
        await state.clear()


async def ask_melody_question(bot, user_id, question, question_number, total_questions):
    # Play song preview (from S3 bucket) for the melody quiz question
    song_url = question['song_url']
    await bot.send_audio(
        user_id, song_url, caption=f"Question {question_number}/{total_questions}: What song is this?"
    )
