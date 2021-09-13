from rest_framework.routers import SimpleRouter

from .views.wallets import ThenewbostonWalletViewSet


router = SimpleRouter(trailing_slash=False)
router.register('tnbc-wallet', ThenewbostonWalletViewSet)
