import requests
import humanize
from django.conf import settings

from core.models.wallets import ThenewbostonWallet

from .models.profile import Profile
from .models.advertisement import Advertisement
from core.utils.shortcuts import convert_to_decimal, comma_seperated_int
from escrow.models.payment_method import PaymentMethod


def get_or_create_user_profile(user):

    obj, created = Profile.objects.get_or_create(user=user)

    return obj


def create_offer_table(side, number_of_data):

    if side == Advertisement.BUY:
        advertisements = Advertisement.objects.filter(status=Advertisement.OPEN, side=Advertisement.BUY).order_by('-price')[:number_of_data]
    else:
        advertisements = Advertisement.objects.filter(status=Advertisement.OPEN, side=Advertisement.SELL).order_by('price')[:number_of_data]

    message = ""
    offers = []
    index = 0

    for advertisement in reversed(advertisements):

        payment_method_message = ""

        payment_methods = PaymentMethod.objects.filter(user=advertisement.owner)

        for payment_method in payment_methods:
            payment_method_message += f"{payment_method.name} | "

        advertisement_owner_stats = get_or_create_user_profile(advertisement.owner)
        updated_at = humanize.naturalday(advertisement.updated_at)

        message += (
            f"AdvID: {advertisement.uuid_hex}; "
            f"Amount: {comma_seperated_int(advertisement.amount)} Leap Coin; Price: {convert_to_decimal(advertisement.price)};"
            f"\nPayment Method(s): {payment_method_message}"
            f"\nMerchant Stats - Total Trades: {advertisement_owner_stats.total_escrows} | Vol: {comma_seperated_int(advertisement_owner_stats.total_tnbc_escrowed)} Leap Coin"
            f"| Positive Feedback: {advertisement_owner_stats.get_positive_feeback_percentage()}%\n"
            f"Last Updated: {updated_at}\n\n"
        )

        if index % 8 == 0:
            offers.append(message)
            message = ""

        index += 1

    if message:
        offers.append(message)

    return offers


def post_trade_to_api(amount, price):

    price_for_api = int(price / 10000)

    data = {
        'amount': amount,
        'rate': price_for_api,
        'api_key': settings.MVP_SITE_API_KEY
    }

    headers = {
        'Content-Type': 'application/json'
    }

    r = requests.post('https://tnbcrow.pythonanywhere.com/recent-trades', json=data, headers=headers)

    if r.status_code == 201:
        return True, r.json()
    return False, r.json()


def get_total_balance_of_all_user():

    wallets = ThenewbostonWallet.objects.filter(balance__gt=settings.TNBC_MULTIPLICATION_FACTOR)

    total_balace = 0

    for wallet in wallets:
        total_balace += wallet.balance

    return total_balace


def get_advertisement_stats():

    total_tnbc = 0

    advertisements = Advertisement.objects.filter(status=Advertisement.OPEN)

    total_advertisements = advertisements.count()

    for adv in advertisements:

        total_tnbc += adv.amount

    return total_advertisements, total_tnbc


async def update_buy_advertisements(bot):

    buy_offer_channel = bot.get_channel(int(settings.TRADE_CHANNEL_ID))
    offers = create_offer_table(Advertisement.BUY, 16)

    async for oldMessage in buy_offer_channel.history():
        await oldMessage.delete()

    await buy_offer_channel.send("**Buy Advertisements**")
    for offer in offers:
        await buy_offer_channel.send(f"```{offer}```")
    await buy_offer_channel.send("Use the command `/adv sell advertisement_id: ID amount_of_tnbc: AMOUNT` to sell Leap Coin to above advertisement.\nOr `/adv create` command to create your own buy/ sell advertisements.")


async def update_sell_advertisements(bot):

    sell_order_channel = bot.get_channel(int(settings.OFFER_CHANNEL_ID))
    offers = create_offer_table(Advertisement.SELL, 16)

    async for oldMessage in sell_order_channel.history():
        await oldMessage.delete()

    await sell_order_channel.send("**Sell Advertisements**")
    for offer in offers:
        await sell_order_channel.send(f"```{offer}```")
    await sell_order_channel.send("Use the command `/adv buy advertisement_id: ID amount: AMOUNT` to buy Leap Coin from the above advertisements.\nOr `/adv create` to create your own buy/ sell advertisement.")
