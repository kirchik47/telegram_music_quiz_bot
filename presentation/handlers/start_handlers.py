from redis.asyncio import Redis
from entities.user import User


redis_pool = Redis()
async def send_welcome(message, state):
    username = message.from_user.username
    args = message.text.split()
    user_id = message.from_user.id
    if len(args) > 1:
        username = message.from_user.username
        logger.info("QUIZ SHARE", extra={'user': username})

        token = args[-1]

        if songs_left.get(user_id):
            songs_left.pop(user_id, None)
            songs_all.pop(user_id, None)
            correct_options_dict.pop(user_id, None)
            quiz_type.pop(user_id, None)
            points.pop(user_id, None)
            cur_playlists.pop(user_id, None)
            max_points.pop(user_id, None)
            questions_left.pop(user_id, None)
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                cache_key = f'share_info:{token}'
                if await redis_pool.exists(cache_key):
                    share_info = await json.loads(redis_pool.get(cache_key))
                    cur_playlists[user_id] = share_info['playlist_id']
                    inviter_user_id = share_info['user_id']
                    quiz_type[user_id] = share_info['quis_type']
                    max_points[user_id] = share_info['max_points']
                    users_seeds[user_id] = share_info['seed']
                else:
                    await bot.send_message(user_id, text="You've been invited to complete a quiz from your friend! Sorry the link has expired, ask your friend for generating a new one.",
                                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                                        InlineKeyboardButton(text='Back to menu', callback_data='menu')]]))
                    return
                print(max_points)
                inviters_info[user_id] = inviter_user_id
                questions_left[user_id] = max_points[user_id]
                points[user_id] = 0

                await message.answer(text=f"Hello {username}! You've been invited to complete a quiz from your friend! Press the button below to start quiz",
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Start quiz', callback_data=f' quiz')]]))
                
    else:
        logger.info("START", extra={'user': username})
        instruction = ""
        with open('instruction.txt', 'r') as f:
            lines = f.readlines()
            for line in lines:
                instruction += line
        
        await bot.send_message(user_id, text=f'''Hello {username}\! It's a bot for creating music quizes\. \
                               Do not forget to challenge your friends\!\n\n''' + instruction,
                               reply_markup=kb.main,
                               parse_mode=ParseMode('MarkdownV2'))