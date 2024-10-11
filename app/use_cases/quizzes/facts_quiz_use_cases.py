from app.domain.repositories_interfaces.quiz_repo import QuizRepoInterface
from app.use_cases.quizzes.melody_quiz_use_cases import QuizUseCases
from app.domain.services_interfaces.aiohttp_service import AiohttpServiceInterface
from app.domain.services_interfaces.genius_service import GeniusServiceInterface
from app.domain.entities.quiz import Quiz
from app.domain.entities.song import Song
from app.domain.entities.question import Question
import random
import json


class FactsQuizUseCases(QuizUseCases):
    def __init__(self, redis_repo: QuizRepoInterface, 
                 aiohttp_service: AiohttpServiceInterface,
                 genius_service: GeniusServiceInterface):
        super().__init__(redis_repo)    
        self.aiohttp_service = aiohttp_service
        self.genius_service = genius_service
        
    async def create(self,
                     quiz_id: str, 
                     user_id: str, 
                     points: int, 
                     quiz_type: bool, 
                     max_points_per_question: int, 
                     songs: list[Song],
                     questions_amount: int):
        quiz = Quiz(id=quiz_id,
                    user_id=user_id,
                    points=points,
                    quiz_type=quiz_type,
                    max_points_per_question=max_points_per_question,
                )
        model_name = 'hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF/llama-3.2-1b-instruct-q8_0.gguf'
        random.shuffle(songs)
        prompt = f'''
        Generate a music facts question suitable for a fan of each song. 
        I will provide you with the description and lyrics of the song. 

        For the song, create one quiz question with four answer options: one correct answer and three distractors. 
        Output the question in a valid JSON format, where the question is an object with the following structure:

        {{
        "question": "[Question Text]",
        "options": [
            "[Option 1]",
            "[Option 2]",
            "[Option 3]",
            "[Option 4]"
        ],
        "correct_answer": "[Index(starting from 0) of Correct Answer]"
        }}

        Ensure that the JSON is formatted as dictionary with one question object. Here are examples:

        {{
            "question": "In Coldplay's song 'Viva La Vida' what does the narrator claim he used to rule?",
            "options": [
            "The seas",
            "The world",
            "The skies",
            "The people"
            ],
            "correct_answer": "1"
        }}

        {{
            "question": "What year was 'Bohemian Rhapsody' by Queen released?",
            "options": [
            "1973",
            "1975",
            "1976",
            "1979"
            ],
            "correct_answer": "1"
        }}
    
        Please format your output exactly as shown, ensuring that each question has the correct structure.

        '''
        
        payload = {
            'model': model_name,
            'messages': [{"role": "system", "content": '''You are a bot for creating questions for music quizes. You always answer in json output format with a question, 4 options and 1 correct answer like this: {"question": your_generated_question, "options": your_generated_options, "correct_answer": your_generated_correct_answer}'''},
                         {"role": "user", "content": ''}],
            'temperature': 0.5,
            'max_tokens': 5000, 
            'example_output': '''Q: Create a question-interesting fact for a music quiz with 4 possible options with only 1 answer for this song: Melanie Martinez - Tag, You're it.
                    A:{{"question": "What is the album that Melanie Martinez released in 2015, and the song 'Tag, You're it' belongs to it?", "options": ["Crybaby", "Dollhouse", "K-12", "Portals"], "correct_answer": "0"'}}
                    
                    Q: Create a question-interesting fact for a music quiz with 4 possible options with only 1 answer for this song: Coldplay - Viva La Vida.
                    A:{{"question": "In Coldplay's song 'Viva La Vida' what does the narrator claim he used to rule?", "options": ["The seas", "The world", "The skies", "The people"], "correct_answer": "1"'}}
                    
                    Q: Create a question-interesting fact for a music quiz with 4 possible options with only 1 answer for this song: Eminem - Mockingbird.
                    A:{{"question": "In Eminem's song 'Mockingbird' who is he primarily addressing in the lyrics?", "options": ["His mother", "His ex-wife", "His fans", "His daughters"], "correct_answer": "3"'}}
                    
                    '''
        }
        songs_info = 'Here are the description and lyrics for the song '
        questions = []
        for i in range(questions_amount):
            info = await self.genius_service.retrieve_info(songs[i].title)
            description = info['description']
            lyrics = info['lyrics']
            print(lyrics)
            songs_info += songs[i].title + ":\nDescription:\n" + description + "\nLyrics:\n" + lyrics + "\n"
            payload['messages'][1]['content'] = prompt + songs_info
            while True:
                resp = await self.aiohttp_service.post('http://localhost:1234/v1/chat/completions', payload)
                resp = resp['choices'][0]["message"]['content']
                try:
                    start = resp.find('{')
                    end = resp.find('}')
                    question_dict = json.loads(resp[start:end+1])
                    questions.append(Question(id=str(i + 1),
                                             quiz_id=quiz.id,
                                             text=question_dict['question'],
                                             options=question_dict['options'],
                                             correct_answer_index=int(question_dict['correct_answer']) - 1))
                    break
                except Exception as e:
                    print(e)
                    continue

            songs_info = 'Here are the descriptions and lyrics for the songs:\n'        
        quiz.questions = questions        
        return quiz
        
