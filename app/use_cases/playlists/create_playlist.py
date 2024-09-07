from app.domain.repositories_interfaces.user_repo import UserRepoInterface


class CreatePlaylistUseCase:
    def __init__(self, user_repo: UserRepoInterface):
        self.user_repo = user_repo
    
