import uuid
import random

from django.db import models

from core.utils.shortcuts import convert_to_int

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

    def __str__(self):
        return f"User: {self.user}; Memo: {self.memo}; Balance: {convert_to_int(self.balance)}; Available: {convert_to_int(self.get_available_balance())}"


def generate_memo(instance):

    while True:

        memo = str(random.randint(100000, 999999))

        if not ThenewbostonWallet.objects.filter(memo=memo).exists():
            return memo


def pre_save_post_receiver(sender, instance, *args, **kwargs):

    if not instance.memo:
        instance.memo = generate_memo(instance)


models.signals.pre_save.connect(pre_save_post_receiver, sender=ThenewbostonWallet)
