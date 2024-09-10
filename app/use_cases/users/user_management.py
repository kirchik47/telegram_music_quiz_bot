from app.domain.entities.user import User

class UserManagementUseCase:
    def __init__(self, sql_user_repo, redis_user_repo):
        self.sql_user_repo = sql_user_repo
        self.redis_user_repo = redis_user_repo

    async def handle_user(self, user: User):
        # Check if the user exists in the database
        user_redis_info = await self.redis_user_repo.get(user)
        if user_redis_info:
            # If the user exists in Redis, return the cached information
            if user.username != user_redis_info.username:
                await self.redis_user_repo.save(user)
        else:
            user_db_info = await self.sql_user_repo.get(user)
            if not user_db_info:
                # Save the new user in the database
                await self.sql_user_repo.save(user)
            elif user.username != user_db_info.username:
                # Update the existing user if the username has changed
                await self.sql_user_repo.update(user)
            await self.redis_user_repo.save(user)
