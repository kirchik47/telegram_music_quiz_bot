from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

async def inline_lists(lst, ids, param, menu=True):
    keyboard = InlineKeyboardBuilder()
    for i, inst in enumerate(lst):
        keyboard.button(text=inst, callback_data=f'{ids[i]} {param}')
    keyboard.button(text='Back to menu', callback_data='menu')
    keyboard = keyboard.adjust(*[1]*len(lst))
    return keyboard.as_markup()

main = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Start "Guess the melody" quiz', callback_data='melody quiz_amount')],
    [InlineKeyboardButton(text='Start "Facts about song" quiz', callback_data='facts quiz_amount')],
    [InlineKeyboardButton(text='Add song', callback_data='choose_playlist_add_song'), 
     InlineKeyboardButton(text='Delete song', callback_data='delete_song')],
    [InlineKeyboardButton(text='Get songs list', callback_data='get_songs'), 
     InlineKeyboardButton(text='Create new playlist', callback_data='create_playlist')],
    [InlineKeyboardButton(text='Delete playlist', callback_data='choose_playlist_delete'), 
     InlineKeyboardButton(text='Search other playlists', callback_data='search')],
    [InlineKeyboardButton(text='Edit playlist information', callback_data='choose_playlist_edit'),
     InlineKeyboardButton(text='Instruction', callback_data='instruction')]
    ],
    input_field_placeholder='Choose an option'
)
