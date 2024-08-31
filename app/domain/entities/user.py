class User:
    def __init__(self, id):
        self.data = {
            id: 'id',
            'username': None,
            'playlists': []
        }
    
    def update(self, field, value):
        self.data[field] = value

    def to_dict(self):
        return self.data
    
    @classmethod
    def from_dict(cls, id, data_dict):
        user = cls(id)
        user.data = data_dict
        return user
