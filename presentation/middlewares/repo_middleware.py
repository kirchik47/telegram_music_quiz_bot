from aiogram import BaseMiddleware


class RepoMiddleware(BaseMiddleware):
    def __init__(self, repo_service):
        super().__init__()
        self.repo_service = repo_service
    
    async def __call__(self, handler, event, data: dict):
        data['repo_service'] = self.repo_service
        return await handler(event, data)
