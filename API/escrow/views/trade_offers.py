from rest_framework import mixins, viewsets

from ..models.trade_offers import TradeOffer
from ..serializers.trade_offers import TradeOfferSerializer


class TradeOfferViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    queryset = TradeOffer.objects.all()
    serializer_class = TradeOfferSerializer
