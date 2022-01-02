from rest_framework import serializers

from ..models.advertisement import Advertisement


class AdvertisementSerializer(serializers.ModelSerializer):

    class Meta:
        model = Advertisement
        fields = ('uuid_hex', 'amount', 'price', 'side')
