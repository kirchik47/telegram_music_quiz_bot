from app.domain.repositories_interfaces.song_repo import SongRepoInterface
from app.domain.entities.song import Song
import aioboto3
import aiohttp
from botocore.exceptions import ClientError


class S3SongRepo(SongRepoInterface):
    def __init__(self, bucket_name: str):
        self.s3_session = aioboto3.Session()
        self.bucket_name = bucket_name

    async def get(self, song: Song) -> bytes:
        async with self.s3_session.client('s3') as s3_client:
            response = await s3_client.get_object(Bucket=self.bucket_name, Key='songs/' + song.title + '.mp3')
        return response['Body'].read()  # Returns the binary data of the song
    
    async def save(self, song: Song, url) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                async with self.s3_session.client('s3') as s3_client:
                    try:
                        # Check if the object already exists
                        await s3_client.head_object(Bucket=self.bucket_name, Key=f'songs/{song.title}.mp3')
                    except ClientError:
                        # If the object doesn't exist, upload it
                        await s3_client.put_object(
                            Bucket=self.bucket_name, 
                            Key=f'songs/{song.title}.mp3', 
                            Body=await response.read()
                        )

    async def delete(self, song: Song) -> None:
        async with self.s3_session.client('s3') as s3_client:
            await s3_client.delete_object(Bucket=self.bucket_name, Key='songs/' + song.title)
