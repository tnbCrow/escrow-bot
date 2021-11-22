import uuid

from django.db import models

from core.models.users import User


class PaymentMethod(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    uuid_hex = models.CharField(max_length=255, unique=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    name = models.CharField(max_length=255)
    detail = models.CharField(max_length=255)
    condition = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


def generate_hex_uuid(instance):

    while True:

        uuid_hex = f'{uuid.uuid4().hex}'

        if not PaymentMethod.objects.filter(uuid_hex=uuid_hex).exists():
            return uuid_hex


def pre_save_post_receiver(sender, instance, *args, **kwargs):

    if not instance.uuid_hex:
        instance.uuid_hex = generate_hex_uuid(instance)


models.signals.pre_save.connect(pre_save_post_receiver, sender=PaymentMethod)
