import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
import requests
import telebot
import re
import mysql.connector 
import shutil
import random


CLIENT_ID = os.getenv('CLIENT_ID')
TG_TOKEN = os.getenv('TG_TOKEN')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
PASSWORD = os.getenv('PASSWORD')
bot = telebot.TeleBot(TG_TOKEN)
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID,
                                                           client_secret=CLIENT_SECRET))
user_state = {}
user_playlist_id = 0
db = mysql.connector.connect(
    host='localhost',
    user='root',
    password=PASSWORD,
    database='songs'
)
cursor = db.cursor(dictionary=True)
def get_song_preview_url(song_id):
    track_info = sp.track(song_id)
    return track_info['preview_url'], track_info['album']['artists'][0]['name'] + " - " + track_info['name']

def download_preview(url, filename):
    response = requests.get(url)
    with open(filename, 'wb') as file:
        file.write(response.content)

def extract_spotify_track_id(url):
    match = re.search(r'https://open\.spotify\.com/track/([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    else:
        return None
    
def get_songs_from_db(playlist_id):
    cursor.execute(f"SELECT * FROM songs WHERE playlist_id={playlist_id}")
    return cursor.fetchall()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    username = message.from_user.username
    bot.reply_to(message, f'''Hello {username}! \nUse the command /add_song <playlist_name> - to start adding songs to your playlist. \n/delete_song <playlist_name> - to start deleting songs from your playlist.\n/get_songs <playlist_name>  - to see the list of the songs from your playlist.''')

@bot.message_handler(commands=['add_song'])
def ask_for_song_id(message):
    try:
        playlist_name = message.text.split()[1]
        try:
            cursor.execute(f"INSERT INTO users VALUES({message.from_user.id});")
            db.commit()
        except:
            pass
        
        cursor.execute(f"SELECT id FROM playlists WHERE user_id={message.from_user.id} AND name='{playlist_name}';")
        if not cursor.fetchall():
            print(cursor.fetchall())
            cursor.execute(f"INSERT INTO playlists(user_id, name) VALUES({message.from_user.id}, '{playlist_name}');")
            db.commit()
        cursor.execute(f"SELECT id FROM playlists WHERE user_id={message.from_user.id} AND name='{playlist_name}';")
        # cursor.execute("SELECT * FROM users")
        global user_playlist_id 
        user_playlist_id = cursor.fetchall()[0]['id']
        username = message.from_user.username
        user_state[message.from_user.id] = 'awaiting_song_id'
        bot.reply_to(message, f'{username}, please provide the Spotify song link to add to the playlist {playlist_name}.')
    except IndexError:
        bot.reply_to(message, 'Please provide a playlist name. Usage: /add_song <playlist_name>')

@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == 'awaiting_song_id')
def add_song_to_playlist(message):
    song_id = extract_spotify_track_id(message.text.strip())
    user_id = message.from_user.id
    print(user_playlist_id)
    cursor.execute(f"SELECT name FROM playlists WHERE id={user_playlist_id}")
    playlist_name = cursor.fetchone()['name']
    print(playlist_name, song_id)
    preview_url, song_name = get_song_preview_url(song_id)
    if preview_url:
        filepath = f'songs/{user_id}/{playlist_name}'
        if not os.path.exists(filepath):
            os.mkdir(filepath)
        filename = os.path.join(filepath, f'{song_name}.mp3')
        download_preview(preview_url, filename)
        cursor.execute(f"INSERT INTO songs VALUES('{song_id}', '{song_name}', {user_playlist_id})")
        db.commit()
        bot.reply_to(message, f'Song with name {song_name} has been added to playlist {playlist_name}.')
        user_state.pop(message.from_user.id, None)
    else:
        bot.reply_to(message, 'Preview not available for this track. Please provide a valid Spotify song ID.')

@bot.message_handler(commands=['start'])
def delete_song_from_playlist(message):
    username = message.from_user.username
    bot.reply_to(message, f'Hello {username}! Use the command /add_song <playlist_name> to start adding songs to your playlist.')

@bot.message_handler(commands=['get_songs', 'delete_song'])
def get_songs(message):
    playlist_name = message.text.split()[1]
    user_id = message.from_user.id
    cursor.execute(f"SELECT id FROM playlists WHERE name='{playlist_name}' AND user_id={user_id}")
    playlist_id = cursor.fetchone()['id']
    print(playlist_id)
    reply = f'Here are the songs from playlist {playlist_name}:\n'
    global songs
    songs = get_songs_from_db(playlist_id)
    for i, song in enumerate(songs):
        reply += f'{i+1}. ' + song['name'] + "\n"

    if message.text.split()[0] == '/delete_song':
        user_state[message.from_user.id] = "awaiting_for_song_idx_del"
        print(user_state)
        reply += "Enter an index of the song you want to delete:"
    bot.reply_to(message, reply)

@bot.message_handler(commands=['get_playlists', 'delete_playlist', 'quiz'])
def get_playlists(message):
    user_id = message.from_user.id
    cursor.execute(f"SELECT name FROM playlists")
    global playlists
    playlists = cursor.fetchall()
    reply = f'Here are your playlists:\n'
    for i, playlist in enumerate(playlists):
        reply += f'{i+1}. ' + playlist['name'] + "\n"

    if message.text.split()[0] == '/delete_playlist':
        user_state[message.from_user.id] = "awaiting_for_playlist_idx_del"
        print(user_state)
        reply += "Enter an index of the playlist you want to delete:"
    if message.text.split()[0] == '/quiz':
        user_state[message.from_user.id] = "awaiting_for_playlist_idx_quiz"
        print(user_state)
        reply += "Enter an index of the playlist to make a quiz based on it:"
    bot.reply_to(message, reply)

@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == 'awaiting_for_song_idx_del')
def delete_song(message):
    song_idx = int(message.text.split()[0])
    user_id = message.from_user.id
    song = songs[song_idx - 1]
    name = song['name']
    playlist_id = song['playlist_id']
    cursor.execute(f"SELECT name FROM playlists WHERE id={playlist_id}")
    playlist_name = cursor.fetchone()['name']
    cursor.execute(f"DELETE FROM songs WHERE name='{name}' AND playlist_id={playlist_id}")
    os.remove(f'songs/{user_id}/{playlist_name}/{name}.mp3')
    db.commit()
    bot.reply_to(message, f"The song {name} was deleted from playlist.")
    user_state.pop(user_id)


@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == 'awaiting_for_playlist_idx_del')
def delete_song(message):
    playlist_idx = int(message.text.split()[0])
    user_id = message.from_user.id
    playlist = playlists[playlist_idx - 1]
    name = playlist['name']
    cursor.execute(f"DELETE FROM playlists WHERE name='{name}' AND user_id={user_id}")
    shutil.rmtree(f'songs/{user_id}/{name}')
    db.commit()
    bot.reply_to(message, f"The playlist {name} was deleted.")
    user_state.pop(user_id)

@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == 'awaiting_for_playlist_idx_quiz')
def start_quiz(message):
    user_id = message.from_user.id
    playlist_idx = int(message.text.split()[0])
    playlist_name = playlists[playlist_idx - 1]['name']

    cursor.execute("""
            SELECT songs.name FROM songs 
            JOIN playlists ON songs.playlist_id = playlists.id
            WHERE playlists.user_id = %s AND playlists.name = %s
        """, (user_id, playlist_name))
    
    songs = cursor.fetchall()
    if len(songs) >= 4:
        songs_list = []
        for song in songs:
            songs_list.append(song['name'])
        random.shuffle(songs_list)
        for song in songs_list:
            incorrect_options = random.sample([song2 for song2 in songs_list if song2 != song], 3)
            song_mp3 = open(f'songs/{user_id}/{playlist_name}/{song}.mp3')
            

    else:
        bot.reply_to(message, "Please add more songs to the playlist(minimal amount of songs - 4).")
bot.infinity_polling()
