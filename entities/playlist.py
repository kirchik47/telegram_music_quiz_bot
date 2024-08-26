class Playlist:
    def __init__(self, playlist_id, name, description, is_public):
        self.data = {
            'id': playlist_id,
            'name': name,
            'description': description,
            'is_public': is_public
        }

    def update(self, field, value):
        self.data[field] = value
