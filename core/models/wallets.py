import uuid
import random

from django.db import models
from django.conf import settings

from .users import User


class ThenewbostonWallet(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)

    balance = models.BigIntegerField(default=0)
    locked = models.BigIntegerField(default=0)
    memo = models.CharField(max_length=255, unique=True)
    withdrawal_address = models.CharField(max_length=64, blank=True, null=True)

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_available_balance(self):
        return self.balance - self.locked

    def get_int_balance(self):
        return int(self.balance / settings.TNBC_MULTIPLICATION_FACTOR)

    def get_int_locked(self):
        return int(self.locked / settings.TNBC_MULTIPLICATION_FACTOR)

    def get_int_available_balance(self):
        return int((self.balance - self.locked) / settings.TNBC_MULTIPLICATION_FACTOR)

    def __str__(self):
        return f"User: {self.user}; Balance: {self.balance}; Available: {self.get_available_balance()}"


# generate a random memo and check if its already taken.
# If taken, generate another memo again until we find a valid memo
def generate_memo(instance):

    while True:

        memo = str(random.randint(100000, 999999))

        if not ThenewbostonWallet.objects.filter(memo=memo).exists():
            return memo


def pre_save_post_receiver(sender, instance, *args, **kwargs):

    if not instance.memo:
        instance.memo = generate_memo(instance)


# save the memo before the User model is saved with the unique memo
models.signals.pre_save.connect(pre_save_post_receiver, sender=ThenewbostonWallet)
