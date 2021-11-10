from uuid import uuid4

from django.db import models
from django.conf import settings

from core.models.users import User


class Profile(models.Model):

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    total_tnbc_escrowed = models.BigIntegerField(default=0)
    total_escrows = models.IntegerField(default=0)
    total_disputes = models.IntegerField(default=0)

    def get_int_total_tnbc_escrowed(self):
        return int(self.total_tnbc_escrowed / settings.TNBC_MULTIPLICATION_FACTOR)

    def __str__(self):
        return f"User: {self.user};"
