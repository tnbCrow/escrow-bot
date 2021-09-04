import uuid

from django.db import models

from core.models.users import User


class Escrow(models.Model):

    OPEN = 'OPEN'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'
    DISPUTE = 'DISPUTE'
    ADMIN_SETTLED = 'ADMIN_SETTLED'
    ADMIN_CANCELLED = 'ADMIN_CANCELLED'

    INITIATOR = 'INITIATOR'
    SUCCESSOR = 'SUCCESSOR'

    settled_towards_choices = [
        (INITIATOR, 'Initiator'),
        (SUCCESSOR, 'Successor')
    ]

    status_choices = [
        (OPEN, 'Open'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
        (DISPUTE, 'Dispute'),
        (ADMIN_SETTLED, 'Admin Settled'),
        (ADMIN_CANCELLED, 'Admin Cancelled')
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    uuid_hex = models.CharField(max_length=255, unique=True)

    amount = models.IntegerField()
    fee = models.IntegerField()
    initiator = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="initiator")
    successor = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="successor")

    status = models.CharField(max_length=255, choices=status_choices)

    initiator_cancelled = models.BooleanField(default=False)
    successor_cancelled = models.BooleanField(default=False)

    agent = models.ForeignKey(User, on_delete=models.DO_NOTHING, blank=True, null=True, related_name="agent")
    settled_towards = models.CharField(max_length=255, choices=settled_towards_choices, default="SUCCESSOR")

    remarks = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Amount: {self.amount}; Status: {self.status}"


# generate a random memo and check if its already taken.
# If taken, generate another memo again until we find a valid memo
def generate_hex_uuid(instance):

    while True:

        uuid_hex = f'{uuid.uuid4().hex}'

        if not Escrow.objects.filter(uuid_hex=uuid_hex).exists():
            return uuid_hex


def pre_save_post_receiver(sender, instance, *args, **kwargs):

    if not instance.uuid_hex:
        instance.uuid_hex = generate_hex_uuid(instance)


# save the memo before the User model is saved with the unique memo
models.signals.pre_save.connect(pre_save_post_receiver, sender=Escrow)
