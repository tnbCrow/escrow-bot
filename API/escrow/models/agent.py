import uuid

from django.db import models


class Agent(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)

    title = models.CharField(max_length=255)
    discord_id = models.IntegerField(unique=True)

    def __str__(self):
        return f"{self.title} - {self.discord_id}"
