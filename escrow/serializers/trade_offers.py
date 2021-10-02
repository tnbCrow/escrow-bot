from rest_framework import serializers

from ..models.trade_offers import TradeOffer


class TradeOfferSerializer(serializers.ModelSerializer):

    class Meta:
        model = TradeOffer
        fields = ('uuid', 'message', 'discord_username', 'created_at', 'updated_at')
