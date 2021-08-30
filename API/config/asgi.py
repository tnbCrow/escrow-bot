import os
from dotenv import load_dotenv
from django.conf import settings

load_dotenv(os.path.join(settings.BASE_DIR, '.env'))

from django.core.asgi import get_asgi_application

DJANGO_SETTINGS_MODULE = os.getenv('DJANGO_SETTINGS_MODULE')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', DJANGO_SETTINGS_MODULE)

application = get_asgi_application()
