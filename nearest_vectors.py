import librosa
import numpy as np
import os
import asyncio
import weaviate
from weaviate.classes.config import DataType, Property, Configure, VectorDistances
from weaviate.classes.query import MetadataQuery, Filter


client = weaviate.use_async_with_local()
async def extract_features(playlist_path, song=None):
    if song is None:
        filenames = list(os.walk(playlist_path))[0][2]
    else:
        filenames = [song]
    print(filenames)
    all_features = np.ndarray(shape=())
    for filename in filenames:
        print(filename)
        y, sr = librosa.load(os.path.join(playlist_path, filename))
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
        all_features = features[:, np.newaxis] if not all_features.shape else np.hstack([all_features, features[:, np.newaxis]])
    return all_features.mean(axis=-1)

async def insert(path, is_public):
    playlist_name = path[path.rfind('/') + 1:]
    user_id = path[path.find('/') + 1:path.rfind('/')]
    await client.connect()
    collection = client.collections.get('Playlists')
    song_collection = client.collections.get('Songs')
    song = list(os.walk(path))[0][2][0]
    print(song)
    song_obj = await song_collection.query.fetch_objects(filters=Filter.by_property('name').equal(song), include_vector=True)
    print(song_obj)
    if song_obj.objects:
        features = song_obj.objects[0].vector['default']
    else:
        features = await extract_features(path)
        await song_collection.data.insert({'name': song}, vector=features.tolist())
    features = await extract_features(path)
    resp = await collection.data.insert({'name': playlist_name, 'user_id': user_id, 'n_songs': 1, 'is_public': is_public}, vector=features.tolist())
    await client.close()

async def update_add_song(path, song):
    playlist_name = path[path.rfind('/') + 1:]
    user_id = path[path.find('/') + 1:path.rfind('/')]
    await client.connect()
    collection = client.collections.get('Playlists')
    song_collection = client.collections.get('Songs')
    song_obj = await song_collection.query.fetch_objects(filters=Filter.by_property('name').equal(song), include_vector=True)
    if song_obj.objects:
        features = song_obj.objects[0].vector['default']
    else:
        features = await extract_features(path, song)
        await song_collection.data.insert({'name': song}, vector=features.tolist())
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

async def search(path, n_questions, offset=None):
    playlist_name = path[path.rfind('/') + 1:]
    await client.connect()
    collection = client.collections.get('Playlists')
    pl = await collection.query.fetch_objects(filters=Filter.by_property('name').equal(playlist_name), include_vector=True)
    print(pl)
    if pl.objects:
        features = pl.objects[0].vector['default']
    else:
        features = (await extract_features(path)).tolist()
    res = await collection.query.near_vector(features, return_metadata=MetadataQuery(distance=True, certainty=True),
                                             limit=4, offset=offset, 
                                             filters=(Filter.by_property('n_songs').greater_or_equal(max(4, n_questions))
                                                      & Filter.by_property('is_public').equal(1)))
    await client.close()
    return res

async def delete_playlist(path):
    playlist_name = path[path.rfind('/') + 1:]
    user_id = path[path.find('/') + 1:path.rfind('/')]
    await client.connect()
    collection = client.collections.get('Playlists')
    data = await collection.query.fetch_objects(filters=(Filter.by_property('name').equal(playlist_name) & 
                                                         Filter.by_property('user_id').equal(user_id)), 
                                                include_vector=True)
    uuid = data.objects[0].uuid
    res = await collection.data.delete_by_id(uuid=uuid)
    await client.close()

async def update_delete_song(path, song):
    playlist_name = path[path.rfind('/') + 1:]
    user_id = path[path.find('/') + 1:path.rfind('/')]
    await client.connect()
    collection = client.collections.get('Playlists')
    song_collection = client.collections.get('Songs')
    song_obj = await song_collection.query.fetch_objects(filters=Filter.by_property('name').equal(song), include_vector=True)
    if song_obj.objects:
        features = song_obj.objects[0].vector['default']
    else:
        features = await extract_features(path, song)
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
    print(await collection.query.fetch_objects(include_vector=True))
    await client.close()

if __name__ == "__main__":
    asyncio.run(main('songs/1150895601/america', 'Coldplay - Fix You.mp3'))
    