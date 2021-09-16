import uuid

from django.db import models


class Statistic(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)

    total_balance = models.BigIntegerField()
    total_fees_collected = models.BigIntegerField()

    total_servers = models.IntegerField()
    total_users = models.IntegerField()

    def get_int_balance(self):
        return int(self.total_balance / 100000000)
    
    def get_int_fees_collected(self):
        return int(self.total_fees_collected / 100000000)

    def __str__(self):
        return f"Balance: {self.total_balance}; Servers: {self.total_servers}; Users: {self.total_users}"
