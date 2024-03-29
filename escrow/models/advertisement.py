import uuid

from django.db import models

from core.models.users import User
from core.utils.shortcuts import convert_to_decimal


class Advertisement(models.Model):

    OPEN = 'OPEN'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'

    BUY = 'BUY'
    SELL = 'SELL'

    status_choices = [
        (OPEN, 'Open'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled')
    ]

    side_choices = [
        (BUY, 'Buy'),
        (SELL, 'Sell')
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    uuid_hex = models.CharField(max_length=255, unique=True)

    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)

    amount = models.BigIntegerField()
    price = models.BigIntegerField()

    status = models.CharField(max_length=255, choices=status_choices)
    side = models.CharField(max_length=255, choices=side_choices)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Amount: {convert_to_decimal(self.amount)}; Price: {convert_to_decimal(self.price)}; Status: {self.status}"


def generate_hex_uuid(instance):

    while True:

        uuid_hex = f'{uuid.uuid4().hex}'
        trimmed_hex = uuid_hex[0:16]

        if not Advertisement.objects.filter(uuid_hex=trimmed_hex).exists():
            return trimmed_hex


def pre_save_post_receiver(sender, instance, *args, **kwargs):

    if not instance.uuid_hex:
        instance.uuid_hex = generate_hex_uuid(instance)


models.signals.pre_save.connect(pre_save_post_receiver, sender=Advertisement)
