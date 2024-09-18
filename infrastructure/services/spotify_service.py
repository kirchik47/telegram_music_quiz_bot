import re
from app.domain.services_interfaces.spotify_service import SpotifyServiceInterface
from async_spotify import SpotifyApiClient
from async_spotify.authentification.authorization_flows import ClientCredentialsFlow


class SpotifyService(SpotifyServiceInterface):
    def __init__(self, client_id: str, client_secret: str):

        self.auth_flow = ClientCredentialsFlow(application_id=client_id, application_secret=client_secret)
        self.client = SpotifyApiClient(authorization_flow=self.auth_flow, hold_authentication=True)

    async def get_preview(self, song_id: str) -> tuple: 
        auth_token = await self.client.get_auth_token_with_client_credentials()
        await self.client.create_new_client()
        track_info = await self.client.track.get_one(song_id, auth_token=auth_token)
        artists = ", ".join([artist['name'] for artist in track_info['artists']])
        return track_info.get('preview_url'), artists + " - " + track_info['name']
    
    async def get_song_id(self, url: str) -> str:
        match = re.search(r'https://open\.spotify\.com/track/([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        else:
            return None
