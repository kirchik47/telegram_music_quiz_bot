import logging
import logging.config


logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(user)s - %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'app.log',
            'formatter': 'standard',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
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
