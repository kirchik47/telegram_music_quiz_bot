from elasticsearch import AsyncElasticsearch, NotFoundError
import os
import asyncio


API_KEY = os.getenv('ES_KEY_DOCKER')
ENDPOINT = os.getenv('ES_ENDPOINT')
client = AsyncElasticsearch("https://localhost:9200/", api_key=API_KEY, ca_certs='ca.crt')

async def add_playlist(id, name, username, desc):
    await client.index(index='playlists', id=id, document={'name': name, 
                                                           'username': username,
                                                           'description': desc})
    await client.close()

async def delete_playlist(id):
    try:
        await client.delete(index='playlists', id=id)
    except NotFoundError:
        pass
    await client.close()

async def search(fields, text):
    query_dict = {"query": {
                    'multi_match': {
                        'query': text,
                        'fields': fields,
                        'fuzziness': 'AUTO'
                        }
                    }
                }
                
    print(await client.async_search.submit(index='playlists', body=query_dict))
    playlists = (await client.async_search.submit(index='playlists', 
                                                  query={'multi_match': {
                                                      'query': text,
                                                      'fields': fields,
                                                      'fuzziness': 'AUTO'
                                                  }}))['response']['hits']['hits']
    await client.close()
    return playlists

async def update(id, field, value):
    await client.update(index='playlists', id=id, doc={field: value})
    await client.close()

async def main():
    index_body = {
        "settings": {
            "analysis": {
                "analyzer": {
                    "my_index_analyzer": {
                        "type": "custom",
                        "tokenizer": "mytokenizer",
                        "filter": [
                            "lowercase",
                            "english_stop"
                        ]
                    },
                    "my_search_analyzer": {
                        "type": "custom",
                        "tokenizer": "mytokenizer",
                        "filter": [
                            "lowercase",
                            "english_stop"
                        ]
                    }
                },
                "filter": {
                    "english_stop":{
                        "type": "stop",
                        "stopwords": "_english_"
                    }
                },
                'tokenizer':{
                    'mytokenizer': {
                        'type': 'standard',
                    }
                }
            },
            'max_ngram_diff': "50"
        },
        "mappings": {
            "properties": {
                "name": {
                    "type": "text",
                    "analyzer": "my_index_analyzer",
                    "search_analyzer": "my_search_analyzer"
                },
                "username": {
                    "type": "text",
                    "analyzer": "my_index_analyzer",
                    "search_analyzer": "my_search_analyzer"
                },
                "desc": {
                    "type": "text",
                    "analyzer": "my_index_analyzer",
                    "search_analyzer": "my_search_analyzer"
                }
            }
        },
    }
    # await client.indices.delete(index='playlists')
    # await client.indices.create(index='playlists', body=index_body)
    # await add_playlist(id=27, name='coldplay mix', username='kirchik47', desc='Coldplay mix, contains only coldplay songs')
    # await add_playlist(id=28, name='Pop mix', username='kirchik47', desc='Pop mix with such artists: Adele, Coldplay, Melanie Martinez, Imagine Dragons etc.')
    # print(await client.indices.analyze(index='playlists', body={'tokenizer': 'my_tokenizer', 'text': 'coldplay'}))
    print(await search(['name', 'username', 'description'], 'coldplay'))

if __name__ == '__main__':
    asyncio.run(main())
    
