from rest_framework import mixins, viewsets

from ..models.advertisement import Advertisement
from ..serializers.advertisement import AdvertisementSerializer


class AdvertisementViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    queryset = Advertisement.objects.filter(status=Advertisement.OPEN)
    serializer_class = AdvertisementSerializer