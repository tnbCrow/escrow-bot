from rest_framework.routers import SimpleRouter

from .views.trade_offers import TradeOfferViewSet
from .views.escrow import EscrowViewSet
from .views.profile import ProfileViewSet

router = SimpleRouter(trailing_slash=False)
router.register('trade-offers', TradeOfferViewSet)
router.register('escrow', EscrowViewSet)
router.register('profile', ProfileViewSet)
