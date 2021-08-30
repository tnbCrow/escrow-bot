from .base import *  # noqa: F401


# Project Artitecture Constants
DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', 'iskush.pythonanywhere.com']

# Business Logic Constants
MIN_TNBC_ALLOWED = 5  # In TNBC
TRADE_CHANNEL_ID = '870848421207101441'
DISPUTE_CHANNEL_ID = '880650616102330428'
AGENT_ROLE_ID = '880650489040085044'
MANAGER_ID = '534628936571813889'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
