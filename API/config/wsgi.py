import os
from decouple import config

from django.core.wsgi import get_wsgi_application

DJANGO_SETTINGS_MODULE = config('DJANGO_SETTINGS_MODULE', default='config.settings.development')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', DJANGO_SETTINGS_MODULE)

application = get_wsgi_application()
