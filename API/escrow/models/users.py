from uuid import uuid4

from django.db import models

from core.models.users import User


class EscrowUser(models.Model):

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    total_tnbc_escrowed = models.IntegerField(default=0)
    total_escrows = models.IntegerField(default=0)
    total_disputes = models.IntegerField(default=0)

    def __str__(self):
        return f"User: {self.user};"
