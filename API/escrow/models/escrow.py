import uuid

from django.db import models

from .user import User


class Escrow(models.Model):

    OPEN = 'OPEN'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'
    ADMIN_SETTLED = 'ADMIN_SETTLED'
    ADMIN_CANCELLED = 'ADMIN_CANCELLED'

    status_choices = [
        (OPEN, 'Open'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
        (ADMIN_SETTLED, 'Admin Settled'),
        (ADMIN_CANCELLED, 'Admin Cancelled')
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)

    amount = models.IntegerField()
    initiator = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="initiator")
    successor = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="successor")

    status = models.CharField(max_length=255, choices=status_choices)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Amount: {self.amount}; Status: {self.status}"
