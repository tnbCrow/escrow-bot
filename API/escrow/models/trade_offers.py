import uuid

from django.db import models

from core.models.users import User


class TradeOffer(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    discord_username = models.CharField(max_length=255)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.discord_username}: {self.message}"
