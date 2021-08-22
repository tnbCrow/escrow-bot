#### tnbCrow Discord Bot

Try `/help` for commands in tnbCrow discord server.

#### Development Guide

- Clone the repo

- Activate the virtual environment. https://docs.python.org/3/library/venv.html

- Install the requirements using `pip install -r requirements.txt`

- Set environment variables `CROW_DISCORD_TOKEN` and `TRADE_CHANNEL_ID`

##### To run discord bot:

- Use command `python bot.py`

##### To run django server

- Go to API directory.

- Use `python manage.py migrate` to create database.

- Create superuser with the command `python manage.py createsuperuser`.

- Login into the Django admin panel and add an entry in ScanTracker table. (only the transactions created after the entry will be tracked)

- Run the server with `python manage.py runserver`.

Happy building!!
