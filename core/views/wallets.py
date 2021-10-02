from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAdminUser

from ..models.wallets import ThenewbostonWallet
from ..serializers.wallets import ThenewbostonWalletSerializer


class ThenewbostonWalletViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    queryset = ThenewbostonWallet.objects.all()
    serializer_class = ThenewbostonWalletSerializer
    permission_classes = [IsAdminUser]
