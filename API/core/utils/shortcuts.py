from ..models.wallets import ThenewbostonWallet
from ..models.users import User


def get_or_create_tnbc_wallet(user):

    obj, created = ThenewbostonWallet.objects.get_or_create(user=user)

    return obj


def get_or_create_discord_user(discord_id):

    obj, created = User.objects.get_or_create(discord_id=str(discord_id))

    return obj
