from rest_framework.routers import SimpleRouter

from .views.escrow import EscrowViewSet
from .views.profile import ProfileViewSet

router = SimpleRouter(trailing_slash=False)
router.register('escrow', EscrowViewSet)
router.register('profile', ProfileViewSet)
