from app.domain.entities.user import User
from app.domain.repositories_interfaces.user_repo import UserRepoInterface

class UserUseCases:
    def __init__(self, sql_repo: UserRepoInterface, redis_repo: UserRepoInterface):
        self.sql_repo = sql_repo
        self.redis_repo = redis_repo

    async def save_user(self, user: User) -> None:
        # Check if the user exists in the redis cache
        redis_info = await self.redis_repo.get(user)
        if redis_info:
            # If the user exists in redis cache and it has a different username, update it
            if user.username != redis_info.username:
                await self.redis_repo.save(user)
            # If the user exists in redis cache and it has the same username, do nothing
        else:
            sql_info = await self.sql_repo.get(user)
            # Save the new user in the database if he is not present
            if not sql_info:
                await self.sql_repo.save(user)
            # Update the existing user if the username has changed
            elif user.username != sql_info.username:
                await self.sql_repo.update(user)
            # Anyways save the user in redis cache because he is not present there
            await self.redis_repo.save(user)
    
    async def get(self, user: User) ->  User:
        # Check if the user exists in the redis cache
        redis_info = await self.redis_repo.get(user)
        if redis_info:
            return redis_info
        return await self.sql_repo.get(user)

    async def update_playlists(self, user: User) -> None:
        await self.redis_repo.save(user)

