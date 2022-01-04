from rest_framework import mixins, viewsets, filters

from django_filters.rest_framework import DjangoFilterBackend

from ..models.advertisement import Advertisement
from ..serializers.advertisement import AdvertisementSerializer


class AdvertisementViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    queryset = Advertisement.objects.filter(status=Advertisement.OPEN)
    serializer_class = AdvertisementSerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    ordering_fields = ['price', 'amount']
    filterset_fields = ['side']
