import aiomysql
import asyncio

class MySQLPool:
    def __init__(self, host: str, port: int, user: str, password: str, db: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db
        self.pool = None

    async def create_pool(self):
        self.pool = await aiomysql.create_pool(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            db=self.db,
        )

    async def close_pool(self):
        self.pool.close()
        await self.pool.wait_closed()

    async def get_connection(self):
        return await self.pool.acquire()

    async def release_connection(self, connection):
        self.pool.release(connection)
        