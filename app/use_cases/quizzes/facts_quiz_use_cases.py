from app.domain.repositories_interfaces.quiz_repo import QuizRepoInterface
from app.use_cases.quizzes.melody_quiz_use_cases import QuizUseCases
from app.domain.services_interfaces.aiohttp_service import AiohttpServiceInterface
from app.domain.services_interfaces.genius_service import GeniusServiceInterface
from app.domain.entities.quiz import Quiz
from app.domain.entities.song import Song
import random


class FactsQuizUseCases(QuizUseCases):
    def __init__(self, redis_repo: QuizRepoInterface, 
                 aiohttp_service: AiohttpServiceInterface,
                 genius_service: GeniusServiceInterface):
        super().__init__(redis_repo)    
        self.aiohttp_service = aiohttp_service
        self.genius_service = genius_service
        
    async def create(self, url,
                     quiz_id: str, user_id: str, 
                     points: int, quiz_type: bool, 
                     max_points_per_question: int, songs: list[Song] 
                     ):
        quiz = Quiz(id=quiz_id,
                    user_id=user_id,
                    points=points,
                    quiz_type=quiz_type,
                    max_points_per_question=max_points_per_question,
                )
        model_name = 'QuantFactory/Meta-Llama-3-8B-GGUF/Meta-Llama-3-8B.Q2_K.gguf'
        random.shuffle(songs)
        n_songs = len(songs)
        prompt = f'''
        Generate a music facts quiz with {n_songs} questions suitable for the person who is a fan of this song.
        I will provide you with the description and lyrics of the song.  
        Each question should have four answer options: one correct answer and three distractors. 
        Format the output clearly as follows:

        Question 1:
        Text: [Question Text]
        Options:
        A) [Option A]
        B) [Option B]
        C) [Option C]
        D) [Option D]
        Correct Answer: [Letter of Correct Answer]

        Question 2:
        Text: [Question Text]
        Options:
        A) [Option A]
        B) [Option B]
        C) [Option C]
        D) [Option D]
        Correct Answer: [Letter of Correct Answer]

        ... and so on for all {n_songs} questions.

        **Example:**

        Question 1:
        Text: In Coldplay's song 'Viva La Vida' what does the narrator claim he used to rule?
        Options:
        A) The seas
        B) The world
        C) The skies
        D) The people
        Correct Answer: B
        '''
        songs_info = ''
        for song in songs:
            info = await self.genius_service.retrieve_info(song.title)
            description = info['description']
            lyrics = info['lyrics']
            
        payload = {
            'model': model_name,
            'messages': [{"role": "system", "content": '''You are a bot for creating questions for music quizes. You always answer in json output format with a question, 4 options and 1 correct answer like this: {"question": your_generated_question, "options": your_generated_options, "correct_answer": your_generated_correct_answer}'''},
                         {"role": "user", "content": prompt}],
            'temperature': 0.2,
            'max_tokens': 5000, 
            'example_output': '''Q: Create a question-interesting fact for a music quiz with 4 possible options with only 1 answer for this song: Melanie Martinez - Tag, You're it.
                    A:{{"question": "What is the album that Melanie Martinez released in 2015, and the song 'Tag, You're it' belongs to it?", "options": ["Crybaby", "Dollhouse", "K-12", "Portals"], "correct_answer": "Crybaby"'}}
                    
                    Q: Create a question-interesting fact for a music quiz with 4 possible options with only 1 answer for this song: Coldplay - Viva La Vida.
                    A:{{"question": "In Coldplay's song 'Viva La Vida' what does the narrator claim he used to rule?", "options": ["The seas", "The world", "The skies", "The people"], "correct_answer": "The world"'}}
                    
                    Q: Create a question-interesting fact for a music quiz with 4 possible options with only 1 answer for this song: Eminem - Mockingbird.
                    A:{{"question": "In Eminem's song 'Mockingbird' who is he primarily addressing in the lyrics?", "options": ["His mother", "His ex-wife", "His fans", "His daughters"], "correct_answer": "His daughters"'}}
                    
                    Q: Create a question-interesting fact for a music quiz with 4 possible options with only 1 answer for this song: {correct_option}.
                    '''
        }
        resp = await self.aiohttp_service.post(url, payload)
        
