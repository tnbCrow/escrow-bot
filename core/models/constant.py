import uuid

from django.db import models


class BotConstant(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)

    title = models.CharField(max_length=255, unique=True)

    tnbc_account_number = models.CharField(max_length=255, default="xyz")
    check_tnbc_confirmation = models.BooleanField(default=False)
    tnbc_bank_ip = models.CharField(max_length=255, default="xyz")

    bot_manager_id = models.BigIntegerField(default=0)
    offer_channel_id = models.BigIntegerField(default=0)
    dispute_channel_id = models.BigIntegerField(default=0)
    agent_role_id = models.BigIntegerField(default=0)
    admin_role_id = models.BigIntegerField(default=0)

    minimum_advertisement_amount = models.BigIntegerField(default=0)
    maximum_advertisement_amount = models.BigIntegerField(default=0)

    minimum_escrow_amount = models.BigIntegerField(default=0)
    maximum_escrow_amount = models.BigIntegerField(default=0)

    def __str__(self):
        return self.title
