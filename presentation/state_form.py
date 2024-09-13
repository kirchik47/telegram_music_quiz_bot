from aiogram.filters.state import State, StatesGroup


class Form(StatesGroup):
    waiting_for_song_id = State()
    waiting_for_playlist_name = State()
    menu = State()
    got_amount = State()
    invite_link = State()
    other_playlist_got_amount = State()
    waiting_for_amount = State()
    waiting_for_description = State()
    waiting_for_search_query = State()
    waiting_for_playlist_name_edit = State()
    waiting_for_playlist_description_edit = State()
    search_got_amount = State()
    