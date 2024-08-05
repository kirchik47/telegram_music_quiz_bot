from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


main = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Start "Guess the melody" quiz', callback_data='melody quiz_amount'), 
     InlineKeyboardButton(text='Start "Facts about song" quiz', callback_data='facts quiz_amount')],
    [InlineKeyboardButton(text='Add song', callback_data='add_song'), 
     InlineKeyboardButton(text='Delete song', callback_data='delete_song')],
    [InlineKeyboardButton(text='Get songs list', callback_data='get_songs'), 
     InlineKeyboardButton(text='Create new playlist', callback_data='create_playlist')],
    [InlineKeyboardButton(text='Delete playlist', callback_data='delete_playlist')]
    ],
    input_field_placeholder='Choose an option'
)
