from app.domain.entities.quiz import Quiz
from abc import ABC, abstractmethod

class QuizRepoInterface(ABC):
    @abstractmethod
    async def get(self, quiz: Quiz) -> Quiz:
        raise NotImplementedError
    
    @abstractmethod
    async def save(self, quiz: Quiz) -> Quiz:
        raise NotImplementedError
    
    @abstractmethod
    async def delete(self, quiz: Quiz) -> Quiz:
        raise NotImplementedError
    
    