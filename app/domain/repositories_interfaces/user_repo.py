from app.domain.entities.user import User
from abc import ABC, abstractmethod

class UserRepoInterface(ABC):
    @abstractmethod
    def get(self, user_id: str) -> User:
        raise NotImplementedError

    @abstractmethod
    def save(self, fields: dict) -> User:
        raise NotImplementedError
    
    @abstractmethod
    def delete(self, user_id: str) -> User:
        raise NotImplementedError
    