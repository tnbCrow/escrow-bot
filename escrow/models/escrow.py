import uuid
from django.conf import settings

from django.db import models

from core.models.users import User


class Escrow(models.Model):

    NEW = 'NEW'
    OPEN = 'OPEN'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'
    DISPUTE = 'DISPUTE'
    ADMIN_SETTLED = 'ADMIN_SETTLED'
    ADMIN_CANCELLED = 'ADMIN_CANCELLED'

    INITIATOR = 'INITIATOR'
    SUCCESSOR = 'SUCCESSOR'

    BUY = 'BUY'
    SELL = 'SELL'

    settled_towards_choices = [
        (INITIATOR, 'Initiator'),
        (SUCCESSOR, 'Successor')
    ]

    status_choices = [
        (NEW, 'New'),
        (OPEN, 'Open'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
        (DISPUTE, 'Dispute'),
        (ADMIN_SETTLED, 'Admin Settled'),
        (ADMIN_CANCELLED, 'Admin Cancelled')
    ]

    side_choices = [
        (BUY, 'Buy'),
        (SELL, 'Sell')
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    uuid_hex = models.CharField(max_length=255, unique=True)

    amount = models.BigIntegerField()
    fee = models.BigIntegerField()
    price = models.BigIntegerField()

    initiator = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="initiator")
    successor = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="successor")

    status = models.CharField(max_length=255, choices=status_choices)
    side = models.CharField(max_length=255, choices=side_choices)

    conversation_channel_id = models.CharField(max_length=255)

    agent = models.ForeignKey(User, on_delete=models.DO_NOTHING, blank=True, null=True, related_name="agent")
    settled_towards = models.CharField(max_length=255, choices=settled_towards_choices, default="SUCCESSOR")

    remarks = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_int_amount(self):
        return int(self.amount / settings.TNBC_MULTIPLICATION_FACTOR)

    def __str__(self):
        return f"Amount: {self.get_int_amount()}; Status: {self.status}"


def generate_hex_uuid(instance):

    while True:

        uuid_hex = f'{uuid.uuid4().hex}'

        if not Escrow.objects.filter(uuid_hex=uuid_hex).exists():
            return uuid_hex


def pre_save_post_receiver(sender, instance, *args, **kwargs):

    if not instance.uuid_hex:
        instance.uuid_hex = generate_hex_uuid(instance)


models.signals.pre_save.connect(pre_save_post_receiver, sender=Escrow)
