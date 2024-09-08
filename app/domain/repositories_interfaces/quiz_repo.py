from app.domain.entities.quiz import Quiz
from abc import ABC, abstractmethod

class QuizRepoInterface(ABC):
    @abstractmethod
    def get(self, quiz: Quiz) -> Quiz:
        raise NotImplementedError
    
    @abstractmethod
    def save(self, quiz: Quiz) -> Quiz:
        raise NotImplementedError
    
    @abstractmethod
    def delete(self, quiz: Quiz) -> Quiz:
        raise NotImplementedError
    
    