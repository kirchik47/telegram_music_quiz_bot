from app.domain.entities.user import User
from abc import ABC, abstractmethod

class UserRepoInterface(ABC):
    @abstractmethod
    def get(self, user: User) -> User:
        raise NotImplementedError

    @abstractmethod
    def save(self, user: User) -> None:
        raise NotImplementedError
    
    @abstractmethod
    def delete(self, user: User) -> None:
        raise NotImplementedError
    