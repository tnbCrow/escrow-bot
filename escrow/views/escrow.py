from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAdminUser

from ..models.escrow import Escrow
from ..serializers.escrow import EscrowSerializer


class EscrowViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    queryset = Escrow.objects.all()
    serializer_class = EscrowSerializer
    permission_classes = [IsAdminUser]
