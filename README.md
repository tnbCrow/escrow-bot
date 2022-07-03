#### tnbCrow Discord Bot

Try `/help` for commands in tnbCrow discord server.

#### Development Guide

- Clone the repo

- Activate the virtual environment. https://docs.python.org/3/library/venv.html

- Install the requirements using `pip install -r requirements.txt`

- Set environment variables:

```shell
TNBCROW_BOT_ACCOUNT_NUMBER (Leap Coin Account Number for receiving payment)
SIGNING_KEY (Leap Coin Signing Key handling payments)
CHECK_TNBC_CONFIRMATION (True or False)
BANK_IP (Bank IP to handle Leap Coin payment)

CROW_DISCORD_TOKEN (Discord bot token)
DJANGO_SETTINGS_MODULE (config.settings.development or config.settings.production)
SECRET_KEY (Django Secret Key)

BOT_MANAGER_ID
TRADE_CHANNEL_ID
DISPUTE_CHANNEL_ID
AGENT_ROLE_ID
GUILD_ID
ADMIN_ROLE_ID
OFFER_CHANNEL_ID
TRADE_CHAT_CATEGORY_ID

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

- Use `python manage.py migrate` to create database.

- Create superuser with the command `python manage.py createsuperuser`.

- Run the server with `python manage.py runserver`.

Happy building!!
