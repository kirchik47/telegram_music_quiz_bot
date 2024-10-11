# Repository service that contains all repositories for SQL, redis, S3 and services.
class RepoService:
    def __init__(self, sql_user_repo, sql_playlist_repo, sql_song_repo,
                 redis_user_repo, redis_playlist_repo, redis_song_repo, 
                 redis_quiz_repo, s3_song_repo, spotify_service,
                 aiohttp_service, genius_service):
        self.sql_user_repo = sql_user_repo
        self.sql_playlist_repo = sql_playlist_repo
        self.sql_song_repo = sql_song_repo
        self.redis_user_repo = redis_user_repo
        self.redis_playlist_repo = redis_playlist_repo
        self.redis_song_repo = redis_song_repo
        self.redis_quiz_repo = redis_quiz_repo
        self.s3_song_repo = s3_song_repo
        self.spotify_service = spotify_service
        self.aiohttp_service = aiohttp_service
        self.genius_service = genius_service
        