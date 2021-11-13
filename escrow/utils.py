from .models.profile import Profile
from .models.advertisement import Advertisement
from core.utils.shortcuts import convert_to_int, convert_to_decimal

from table2ascii import table2ascii, PresetStyle


def get_or_create_user_profile(user):

    obj, created = Profile.objects.get_or_create(user=user)

    return obj


def create_offer_table(number_of_data):

    advertisements = Advertisement.objects.filter(status=Advertisement.OPEN).order_by('-price')[:number_of_data]

    temp = []
    body_list = []

    for advertisement in advertisements:
        temp.extend([advertisement.uuid_hex, str(convert_to_int(advertisement.amount)), str(convert_to_decimal(advertisement.price)), advertisement.payment_method])
        body_list.append(temp)
        temp = []

    formatted_table = table2ascii(
        header=["ID", "Amount", "Price (USDT)", "Payment Method"],
        body=body_list,
        style=PresetStyle.ascii_box
    )

    return formatted_table
