from app.domain.repositories_interfaces.quiz_repo import QuizRepoInterface
from app.domain.entities.quiz import Quiz
from app.domain.entities.song import Song
from app.domain.entities.question import Question
import time
import random


class QuizUseCases:
    def __init__(self, redis_repo: QuizRepoInterface):
        self.redis_repo = redis_repo
    
    async def create(self, quiz_id: str, user_id: str, 
                     points: int, quiz_type: bool, 
                     max_points_per_question: int, songs: list[Song], 
                     questions_amount: int) -> Quiz:
        """
        Creates a new quiz with associated questions and options.

        This method creates the entire quiz at once to optimize the latency 
        for LLM generation and improve user experience by reducing the waiting 
        time for each individual question.

        :param quiz_id: The unique identifier for the quiz.
        :param user_id: The ID of the user creating the quiz.
        :param points: The initial points for the quiz.
        :param quiz_type: A boolean indicating the type of the quiz.
        :param max_points_per_question: The maximum points that can be earned per question.
        :param songs: A list of Song objects to be used in the quiz.
        :param texts: A list of question texts corresponding to the songs.
        :return: The created Quiz object.
        """
        quiz = Quiz(id=quiz_id,
                    user_id=user_id,
                    points=points,
                    quiz_type=quiz_type,
                    max_points_per_question=max_points_per_question,
                )
        questions = []
        n_songs = len(songs)
        random.shuffle(songs)
        for i, song in enumerate(songs):
            if i > questions_amount - 1:
                break
            """
            Simple sampling won't be the best way to get random 3 options since we need to provide
            a list for random.sample without the correct answer song. So the time complexity overall 
            will be O(n^2), where n = n_songs. I'm optimizing it by adding randomly generated indices
            to the set so that I check both the repetition and the match with the correct answer.
            So the time complexity will be O(n).
            """ 
            incorrect_indices = set()
            incorrect_options = []
            while len(incorrect_indices) < 3:
                rand_idx = random.randint(0, n_songs - 1)
                if rand_idx != i:
                    incorrect_indices.add(rand_idx)
                
            incorrect_options = [songs[idx] for idx in list(incorrect_indices)]
            options = incorrect_options + [song]
            random.shuffle(options)
            correct_answer_idx = options.index(song)
            question = Question(
                id=str(i),
                quiz_id=quiz.id,
                text=f"Question {i + 1}/{questions_amount}:\n🎵What's this song?🎵",
                options=options,
                correct_answer_index=correct_answer_idx
            )
            questions.append(question)
        quiz.questions = questions
        await self.redis_repo.save(quiz)
        # For future use
        return quiz
    
    async def save(self, 
                   quiz_id: str, 
                   user_id: str, 
                   points: int,
                   quiz_type: bool,
                   max_points_per_question: int,
                   questions: list[Question]) -> None:
        quiz = Quiz(
            id=quiz_id,
            user_id=user_id,
            points=points,
            quiz_type=quiz_type,
            max_points_per_question=max_points_per_question,
            questions=questions
        )
        await self.redis_repo.save(quiz)
    async def get(self, quiz_id: str) -> Quiz:
        """
        Retrieves a quiz by its ID from the Redis repository.

        :param quiz_id: The unique identifier for the quiz to retrieve.
        :return: The retrieved Quiz object.
        """
        quiz = Quiz(id=quiz_id)
        return await self.redis_repo.get(quiz=quiz)
    
    async def delete(self, quiz_id: str) -> None:
        """
        Deletes a quiz by its ID from the Redis repository.
        """
        quiz = Quiz(id=quiz_id)
        await self.redis_repo.delete(quiz=quiz)

    async def add_points(self, quiz_id: str, question_id: str, max_time=30, min_points=20, decay_factor=1):
        """
        Adds points to a quiz based on the time taken to answer a question.

        Points decay based on how long the user took to answer the question.

        :param quiz_id: The unique identifier of the quiz to update.
        :param question_id: The ID of the question for which points are being added.
        :param max_time: The maximum allowed time for answering the question (default is 30 seconds).
        :param min_points: The minimum amount of points secured by answering correctly (default is 20 points).
        :param decay_factor: The factor controlling how quickly points drop off with increasing time (default is 1).
        """
        quiz = await self.get(quiz_id=quiz_id)
        for question in quiz.questions:
            if question.id == question_id:
                time_taken = (time.time() - question.start_time) 
                quiz.points += min_points + int((quiz.max_points_per_question - min_points) 
                                                * ((max_time - min(time_taken, max_time)) /  max_time)**decay_factor)
        await self.redis_repo.save(quiz)
        return quiz # For future use
