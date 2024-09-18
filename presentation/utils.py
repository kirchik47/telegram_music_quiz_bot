import aiofiles
import logging
import hashlib
import time
import presentation.keyboards as kb


logger = logging.getLogger('utils')

# Gets instruction from .txt file
async def get_instruction():
    instruction = ""
    async with aiofiles.open('presentation/instruction.txt', 'r') as f:
        lines = await f.readlines()
        for line in lines:
            instruction += line
    return instruction

# Error handler for cathing errors in different functions
def error_handler(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            obj = args[0]
            user_id = obj.from_user.id
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            await obj.bot.send_message(user_id,
                                       text="Something went wrong. Please try again later.",
                                       reply_markup=await kb.inline_lists([], [], ''))
    return wrapper

async def generate_quiz_id(playlist_name, user_id):
    raw_string = f"{playlist_name}{user_id}" 
    return f"{hashlib.sha256(raw_string.encode()).hexdigest()[:16]}" 

async def generate_playlist_id(playlist_name, user_id):
    raw_string = f"{playlist_name}{user_id}{time.time()}" # Adding current time to generate unique id and prevent collision
    return f"{hashlib.sha256(raw_string.encode()).hexdigest()[:16]}" 
