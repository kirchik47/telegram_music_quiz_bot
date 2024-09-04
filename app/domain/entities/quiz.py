class Quiz:
    def __init__(self, id):
        self.data = {
            'id': id,
            'username': None,
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
        }
    
    def update(self, field, value):
        self.data[field] = value

    def to_dict(self) -> dict:
        return self.data
    
    @classmethod
    def from_dict(cls, id, data_dict) -> 'Quiz':
        user = cls(id)
        user.data = data_dict
        return user