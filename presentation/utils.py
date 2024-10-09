import aiofiles
import logging
import hashlib
import time
import presentation.keyboards as kb


logger = logging.getLogger('utils')

async def get_instruction():
    """
    Asynchronously retrieves the instruction text from a .txt file.

    Reads the content of 'presentation/instruction.txt' and concatenates 
    all lines into a single string.

    :return: A string containing the instructions.
    """
    instruction = ""
    async with aiofiles.open('presentation/instruction.txt', 'r') as f:
        lines = await f.readlines()
        for line in lines:
            instruction += line
    return instruction


def error_handler(func):
    """
    A decorator that wraps asynchronous functions to handle exceptions.

    If an exception occurs in the wrapped function, the error is logged, 
    and a message is sent to the user indicating that something went wrong.

    :param func: The asynchronous function to be wrapped.
    :return: The wrapped function with error handling.
    """
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
    """
    Generates a unique quiz ID based on the playlist name and user ID.

    The quiz ID is created by hashing a combination of the playlist name 
    and user ID using the SHA-256 algorithm, and then truncating it to 
    the first 16 characters.

    :param playlist_name: The name of the playlist.
    :param user_id: The unique identifier for the user.
    :return: A string representing the generated quiz ID.
    """
    raw_string = f"{playlist_name}{user_id}" 
    return f"{hashlib.sha256(raw_string.encode()).hexdigest()[:16]}" 


async def generate_playlist_id(playlist_name, user_id):
    """
    Generates a unique playlist ID based on the playlist name and user ID.

    The playlist ID is created by hashing a combination of the playlist 
    name and user ID using the SHA-256 algorithm, and then truncating it 
    to the first 16 characters.

    :param playlist_name: The name of the playlist.
    :param user_id: The unique identifier for the user.
    :return: A string representing the generated playlist ID.
    """
    raw_string = f"{playlist_name}{user_id}" 
    return f"{hashlib.sha256(raw_string.encode()).hexdigest()[:16]}"
