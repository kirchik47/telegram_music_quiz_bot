from redis.asyncio import Redis
from entities.user import User
import logging
from messages import START_MSG


logger = logging.getLogger('handlers')

redis_pool = Redis()
async def start(message, state):
    logger.info("START", extra={'user': username})
    instruction = ""
    with open('instruction.txt', 'r') as f:
        lines = f.readlines()
        for line in lines:
            instruction += line
    
    await bot.send_message(user_id, text= START_MSG.format(username) + instruction,
                            reply_markup=kb.main,
                            parse_mode=ParseMode('MarkdownV2'))