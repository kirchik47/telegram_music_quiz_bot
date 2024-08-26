class User:
    def __init__(self, id, username):
        self.id = id
        self.username = username
        self.data = {
            'cur_playlists': [],
            'songs_left': [],
            'questions_left': None,
            'max_amount': None,
            'points': None,
            'max_points': None,
            'correct_options': [],
            'inviters_info': [],
            'songs_all': [],
            'quiz_type': None,
            'counter': 0
        }
    
    def update(self, field, value):
        self.data[field] = value
# cur_playlists = {}
# songs_left = {}
# questions_left = {}
# max_amount = {}
# points = {}
# max_points = {}
# correct_options_dict = {}
# inviters_info = {}
# songs_all = {}
# quiz_type = {}
# counter = 0
# users_seeds = {}
# generated_questions = {}   