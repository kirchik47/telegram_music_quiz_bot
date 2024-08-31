class Playlist:
    def __init__(self, playlist_id):
        self.data = {
            'id': playlist_id,
            'name': None,
            'description': None,
            'is_public': None,
            'songs': []
        }

    def update(self, field, value):
        self.data[field] = value
    
    def to_dict(self):
        return self.data
    
    @classmethod
    def from_dict(cls, id, data_dict):
        playlist = cls(id)
        playlist.data = data_dict
        return playlist
