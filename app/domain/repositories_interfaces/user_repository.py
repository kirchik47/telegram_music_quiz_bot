from entities.user import User
from abc import ABC, abstractmethod

class UserRepositoryInterface(ABC):
    @abstractmethod
    def get_by_id(self, user_id: str) -> User:
        raise NotImplementedError

    @abstractmethod
    def save(self, fields: dict) -> User:
        raise NotImplementedError
    
    @abstractmethod
    def delete_by_id(self, user_id: str) -> User:
        raise NotImplementedError
    
    @abstractmethod
    def update_by_id(self, user_id: str, fields: dict) -> User:
        raise NotImplementedError
    