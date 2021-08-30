import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(os.path.join(BASE_DIR, '.env'))

from django.core.wsgi import get_wsgi_application

DJANGO_SETTINGS_MODULE = os.getenv('DJANGO_SETTINGS_MODULE')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', DJANGO_SETTINGS_MODULE)

application = get_wsgi_application()
