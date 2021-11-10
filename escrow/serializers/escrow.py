from rest_framework import serializers

from ..models.escrow import Escrow


class EscrowSerializer(serializers.ModelSerializer):

    class Meta:
        model = Escrow
        fields = ('uuid_hex', 'initiator', 'successor', 'amount', 'fee', 'status')
