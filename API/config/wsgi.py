import os
from dotenv import load_dotenv
from django.conf import settings

load_dotenv(os.path.join(settings.BASE_DIR, '.env'))

from django.core.wsgi import get_wsgi_application

DJANGO_SETTINGS_MODULE = os.getenv('DJANGO_SETTINGS_MODULE')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', DJANGO_SETTINGS_MODULE)

application = get_wsgi_application()
