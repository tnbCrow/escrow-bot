from rest_framework import serializers

from ..models.wallets import ThenewbostonWallet


class ThenewbostonWalletSerializer(serializers.ModelSerializer):

    class Meta:
        model = ThenewbostonWallet
        fields = '__all__'
        depth = 1
