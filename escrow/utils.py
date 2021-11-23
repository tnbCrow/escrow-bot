from .models.profile import Profile
from .models.advertisement import Advertisement
from core.utils.shortcuts import convert_to_int, convert_to_decimal
from escrow.models.payment_method import PaymentMethod


def get_or_create_user_profile(user):

    obj, created = Profile.objects.get_or_create(user=user)

    return obj


def create_offer_table(number_of_data):

    advertisements = Advertisement.objects.filter(status=Advertisement.OPEN).order_by('price')[:number_of_data]

    message = ""

    for advertisement in reversed(advertisements):

        payment_method_message = ""

        payment_methods = PaymentMethod.objects.filter(user=advertisement.owner)

        for payment_method in payment_methods:
            payment_method_message += f"{payment_method.name} | "

        message += f"Advertisement ID: {advertisement.uuid_hex}; Amount: {convert_to_int(advertisement.amount)} TNBC; Price: {convert_to_decimal(advertisement.price)} USDT; Payment Method(s): {payment_method_message}\n\n"

    return message
