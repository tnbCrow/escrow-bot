#### tnbCrow Discord Bot

Try `/help` for commands in tnbCrow discord server.

#### Development Guide

- Clone the repo

- Activate the virtual environment. https://docs.python.org/3/library/venv.html

- Install the requirements using `pip install -r requirements.txt`

- Set environment variables:
```shell
CROW_DISCORD_TOKEN (Discord bot token)
DJANGO_SETTINGS_MODULE (config.settings.development or config.settings.production)
SECRET_KEY (Django Secret Key)
SIGNING_KEY (TNBC Signing Key handling payments)

# For production
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
POSTGRES_PORT
```

You'll also need to update the constants on development.py file according to your setup.

##### To run discord bot:

- Use command `python escrow-bot.py`

##### To run django server

- Go to API directory.

- Use `python manage.py migrate` to create database.

- Create superuser with the command `python manage.py createsuperuser`.

- Login into the Django admin panel and add an entry in ScanTracker table. (only the transactions created after the entry will be tracked)

- Run the server with `python manage.py runserver`.

Happy building!!
