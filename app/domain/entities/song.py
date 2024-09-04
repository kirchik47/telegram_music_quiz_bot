class Song:
    def __init__(self, id, title, spotify_url):
        self.data = {
            'id': id,
            'title': title,
            'spotify_url': spotify_url
        }
    
    def to_dict(self) -> dict:
        return self.data
    