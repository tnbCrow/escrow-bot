from rest_framework.routers import SimpleRouter

from .views.trade_offers import TradeOfferViewSet

router = SimpleRouter(trailing_slash=False)
router.register('trade-offers', TradeOfferViewSet)
