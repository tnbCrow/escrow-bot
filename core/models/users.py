from uuid import uuid4

from django.db import models

from core.utils.shortcuts import convert_to_int
from ..models.transactions import Transaction


class User(models.Model):

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)

    discord_id = models.CharField(max_length=255, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.discord_id


class UserTransactionHistory(models.Model):

    DEPOSIT = 'DEPOSIT'
    WITHDRAW = 'WITHDRAW'
    REFUND = 'REFUND'
    TAKEBACK = 'TAKEBACK'

    type_choices = [
        (DEPOSIT, 'Deposit'),
        (WITHDRAW, 'Withdraw'),
        (REFUND, 'Refund'),
        (TAKEBACK, 'Takeback')
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)

    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    type = models.CharField(max_length=255, choices=type_choices)
    amount = models.BigIntegerField()
    transaction = models.ForeignKey(Transaction, on_delete=models.DO_NOTHING, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"User: {self.user} - {self.type} - {convert_to_int(self.amount)}"
