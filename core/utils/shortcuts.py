from ..models.wallets import ThenewbostonWallet
from ..models.users import User
from django.conf import settings


def get_or_create_tnbc_wallet(user):

    obj, created = ThenewbostonWallet.objects.get_or_create(user=user)

    return obj


def get_or_create_discord_user(discord_id):

    obj, created = User.objects.get_or_create(discord_id=str(discord_id))

    return obj


def convert_to_decimal(amount):

    amount = amount / settings.TNBC_MULTIPLICATION_FACTOR
    rounded_amount = round(amount, 4)
    return rounded_amount
