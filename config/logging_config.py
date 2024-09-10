import logging
import logging.config


class UserFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'user'):
            record.user = 'SYSTEM'  # Set default user if not provided
        return True
    

logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(user)s - %(message)s'
        },
    },
    'filters': {
        'user_filter': {
            '()': UserFilter,
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'C:\\Users\\kirch\\pythonProject\\music_bot\\telegram_music_quiz_bot\\app.log',
            'formatter': 'standard',
            'filters': ['user_filter']
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'filters': ['user_filter']
        },
    },
    'loggers': {
        'use_cases': {  
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'handlers': {  
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'external_apis': {  
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'utils': { 
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        '': {  
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        }
    }
}

logging.config.dictConfig(logging_config)
