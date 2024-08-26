import librosa
import numpy as np
import os
import asyncio
import weaviate
from weaviate.classes.config import DataType, Property, Configure, VectorDistances
from weaviate.classes.query import MetadataQuery, Filter
from redis.asyncio import Redis 
import json


client = weaviate.use_async_with_local()
redis_pool = Redis()
async def extract_features(song):
    filename = song + '.mp3'

    y, sr = librosa.load(os.path.join('songs', filename))
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
    tonnetz = librosa.feature.tonnetz(y=y, sr=sr)
    zcr = librosa.feature.zero_crossing_rate(y)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    print(mfccs.shape, chroma.shape, spectral_contrast.shape, tonnetz.shape, zcr.shape, tempo.shape)
    features = np.hstack([
        np.mean(mfccs, axis=1),
        np.mean(chroma, axis=1),
        np.mean(spectral_contrast, axis=1),
        np.mean(tonnetz, axis=1),
        np.mean(zcr),
        tempo
    ])
    return features

async def insert(playlist_name, user_id, song, is_public):
    await client.connect()
    user_id = str(user_id)
    collection = client.collections.get('Playlists')
    cache_key = f'song-vector:{song}'
    if await redis_pool.exists(cache_key):
        features = json.loads(await redis_pool.get(cache_key))
    else:
        song_collection = client.collections.get('Songs')
        song_obj = await song_collection.query.fetch_objects(filters=Filter.by_property('name').equal(song), include_vector=True)
        print(song_obj)
        if song_obj.objects:
            features = song_obj.objects[0].vector['default']
        else:
            features = await extract_features(song)
            print(features)
            await song_collection.data.insert({'name': song}, vector=features.tolist())
            features = features.tolist()
        await redis_pool.set(cache_key, json.dumps(features), ex=1200)

    resp = await collection.data.insert({'name': playlist_name, 'user_id': user_id, 'n_songs': 1, 'is_public': is_public}, 
                                        vector=features)
    await client.close()

async def update_add_song(playlist_name, user_id, song):
    await client.connect()
    user_id = str(user_id)
    collection = client.collections.get('Playlists')
    cache_key = f'song-vector:{song}'
    if await redis_pool.exists(cache_key):
        features = json.loads(await redis_pool.get(cache_key))
    else:
        song_collection = client.collections.get('Songs')
        song_obj = await song_collection.query.fetch_objects(filters=Filter.by_property('name').equal(song), include_vector=True)
        if song_obj.objects:
            features = song_obj.objects[0].vector['default']
        else:
            features = await extract_features(song)
            await song_collection.data.insert({'name': song}, vector=features.tolist())
            features = features.tolist()
        await redis_pool.set(cache_key, json.dumps(features), ex=1200)
    
    data = await collection.query.fetch_objects(filters=(Filter.by_property('name').equal(playlist_name) & 
                                                         Filter.by_property('user_id').equal(user_id)), 
                                                include_vector=True)
    uuid = data.objects[0].uuid
    vector = data.objects[0].vector['default']
    n_songs = data.objects[0].properties['n_songs'] 
    print(vector)
    for i in range(len(vector)):
        vector[i] = n_songs/(n_songs + 1) * vector[i] + features[i] / n_songs 
    print(vector)
    resp = await collection.data.update(uuid=uuid, properties={'n_songs': n_songs + 1}, vector=vector)
    await client.close()

async def update_name(playlist_name, user_id, new_name):
    await client.connect()
    user_id = str(user_id)
    collection = client.collections.get('Playlists')
    data = await collection.query.fetch_objects(filters=(Filter.by_property('name').equal(playlist_name) & 
                                                         Filter.by_property('user_id').equal(user_id)))
    uuid = data.objects[0].uuid
    await collection.data.update(uuid=uuid, properties={'name': new_name})

async def search(playlist_name, user_id, n_questions, offset=None):
    await client.connect()
    user_id = str(user_id)
    collection = client.collections.get('Playlists')
    pl = await collection.query.fetch_objects(filters=(Filter.by_property('name').equal(playlist_name) & 
                                                       Filter.by_property('user_id').equal(user_id)), include_vector=True)
    features = pl.objects[0].vector['default']
    res = await collection.query.near_vector(features, return_metadata=MetadataQuery(distance=True, certainty=True),
                                             limit=4, 
                                             filters=(Filter.by_property('n_songs').greater_or_equal(max(4, n_questions))
                                                      & Filter.by_property('is_public').equal(1) 
                                                      & Filter.by_property('user_id').not_equal(user_id)))
    await client.close()
    return res

async def delete_playlist(playlist_name, user_id):
    await client.connect()
    playlist_name = str(playlist_name)
    user_id = str(user_id)
    collection = client.collections.get('Playlists')
    data = await collection.query.fetch_objects(filters=(Filter.by_property('name').equal(playlist_name) & 
                                                         Filter.by_property('user_id').equal(user_id)), 
                                                include_vector=True)
    uuid = data.objects[0].uuid
    res = await collection.data.delete_by_id(uuid=uuid)
    await client.close()

async def update_delete_song(playlist_name, user_id, song):
    await client.connect()
    user_id = str(user_id)
    collection = client.collections.get('Playlists')
    cache_key = f'song-vector:{song}'
    if await redis_pool.exists(cache_key):
        features = json.loads(await redis_pool.get(cache_key))
        print('redis')
    else:
        song_collection = client.collections.get('Songs')
        song_obj = await song_collection.query.fetch_objects(filters=Filter.by_property('name').equal(song), include_vector=True)
        if song_obj.objects:
            features = song_obj.objects[0].vector['default']
        else:
            features = await extract_features(song)
            features = features.tolist()
        await redis_pool.set(cache_key, json.dumps(features), ex=1200)
    print(features)
    data = await collection.query.fetch_objects(filters=(Filter.by_property('name').equal(playlist_name) & 
                                                         Filter.by_property('user_id').equal(user_id)), 
                                                include_vector=True)
    uuid = data.objects[0].uuid
    vector = data.objects[0].vector['default']
    n_songs = data.objects[0].properties['n_songs'] 
    print(vector)
    if n_songs > 1:
        for i in range(len(vector)):
            vector[i] = ((vector[i] - features[i] / (n_songs - 1)) * n_songs) / (n_songs - 1)
        await collection.data.update(uuid=uuid, properties={'n_songs': n_songs - 1}, vector=vector)
    else:
        await collection.data.delete_by_id(uuid=uuid)
    await client.close()

async def main(path, song=None):
    client = weaviate.use_async_with_local()
    await client.connect()
    collection = client.collections.get('Playlists')
    # await collection.config.add_property(Property(name='is_public', data_type=DataType.INT))
    # await delete_playlist(path)
    # await update_delete_song('Coldplay mix', 1150895601, 'One Direction - Night Changes')
    print(await collection.query.fetch_objects(include_vector=True))
    await client.close()
    await redis_pool.aclose()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main('songs/1150895601/Pop mix', 'Coldplay - Fix You.mp3'))
    loop.close()
    