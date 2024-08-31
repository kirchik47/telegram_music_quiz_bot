from redis.asyncio import Redis


class RedisPool:
    def __init__(self, host: str, port: int, db: int):
        self.host = host
        self.port = port
        self.db = db
        self.pool = None

    async def create_pool(self):
        self.pool = await Redis(host=self.host, port=self.port, db=self.db)


    async def close_pool(self):
        await self.pool.close()
