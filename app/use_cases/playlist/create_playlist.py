from app.domain.repositories_interfaces.user_repository import UserRepositoryInterface


class CreatePlaylistUseCase:
    def __init__(self, user_repository: UserRepositoryInterface):
        self.user_repository = user_repository
    
