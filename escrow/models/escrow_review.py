import uuid

from django.db import models

from core.models.users import User
from .escrow import Escrow


class EscrowReview(models.Model):

    GOOD = 'GOOD'
    BAD = 'BAD'
    NEUTRAL = 'NEUTRAL'

    feedback_choices = [
        (GOOD, 'Good'),
        (BAD, 'Bad'),
        (NEUTRAL, 'Neutral')
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)

    escrow = models.ForeignKey(Escrow, on_delete=models.DO_NOTHING)
    feedback_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)

    feedback = models.CharField(max_length=255, choices=feedback_choices)

    def __str__(self):
        return f"{self.escrow} - {self.feedback}"
