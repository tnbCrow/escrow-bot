import os

from dotenv import load_dotenv

project_folder = os.path.expanduser('~/crow bot')  # adjust as appropriate
load_dotenv(os.path.join(project_folder, '.env'))

from django.core.asgi import get_asgi_application

DJANGO_SETTINGS_MODULE = os.getenv('DJANGO_SETTINGS_MODULE')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', DJANGO_SETTINGS_MODULE)

application = get_asgi_application()
