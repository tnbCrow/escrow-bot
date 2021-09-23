import uuid

from django.db import models
from django.conf import settings


class Statistic(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)

    title = models.CharField(max_length=255)
    total_balance = models.BigIntegerField(default=0)
    total_fees_collected = models.BigIntegerField(default=0)

    total_servers = models.IntegerField(default=0)
    total_users = models.IntegerField(default=0)

    def get_int_balance(self):
        return int(self.total_balance / settings.TNBC_MULTIPLICATION_FACTOR)

    def get_int_fees_collected(self):
        return int(self.total_fees_collected / settings.TNBC_MULTIPLICATION_FACTOR)

    def __str__(self):
        return f"Balance: {self.total_balance}; Servers: {self.total_servers}; Users: {self.total_users}"
