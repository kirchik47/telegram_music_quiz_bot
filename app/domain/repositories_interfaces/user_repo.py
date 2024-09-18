from app.domain.entities.user import User
from abc import ABC, abstractmethod

class UserRepoInterface(ABC):
    @abstractmethod
    async def get(self, user: User) -> User:
        raise NotImplementedError

    @abstractmethod
    async def save(self, user: User) -> None:
        raise NotImplementedError
    
    @abstractmethod
    async def delete(self, user: User) -> None:
        raise NotImplementedError
    