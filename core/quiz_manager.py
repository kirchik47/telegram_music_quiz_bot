import aiohttp


async def generate_question(prompt, url, model):
    async with aiohttp.ClientSession() as session:
        payload = {
            'model': model,
            'messages': [{"role": "system", "content": '''You are a bot for creating questions for music quizes. You always answer in json output format with a question, 4 options and 1 correct answer like this: {"question": your_generated_question, "options": your_generated_options, "correct_answer": your_generated_correct_answer}'''},
                         {"role": "user", "content": prompt}],
            'temperature': 0.9,
            'max_tokens': 200, 
            'example_output': '''Q: Create a question-interesting fact for a music quiz with 4 possible options with only 1 answer for this song: Melanie Martinez - Tag, You're it.
                    A:{{"question": "What is the album that Melanie Martinez released in 2015, and the song 'Tag, You're it' belongs to it?", "options": ["Crybaby", "Dollhouse", "K-12", "Portals"], "correct_answer": "Crybaby"'}}
                    
                    Q: Create a question-interesting fact for a music quiz with 4 possible options with only 1 answer for this song: Coldplay - Viva La Vida.
                    A:{{"question": "In Coldplay's song 'Viva La Vida' what does the narrator claim he used to rule?", "options": ["The seas", "The world", "The skies", "The people"], "correct_answer": "The world"'}}
                    
                    Q: Create a question-interesting fact for a music quiz with 4 possible options with only 1 answer for this song: Eminem - Mockingbird.
                    A:{{"question": "In Eminem's song 'Mockingbird' who is he primarily addressing in the lyrics?", "options": ["His mother", "His ex-wife", "His fans", "His daughters"], "correct_answer": "His daughters"'}}
                    
                    Q: Create a question-interesting fact for a music quiz with 4 possible options with only 1 answer for this song: {your answer}.
                    '''
        }
        async with session.post(url, json=payload) as response:
            result = await response.json()
            return result['choices'][0]["message"]['content']
        