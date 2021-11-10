from rest_framework import mixins, viewsets

from ..models.escrow import Escrow
from ..serializers.escrow import EscrowSerializer


class EscrowViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    queryset = Escrow.objects.all()
    serializer_class = EscrowSerializer
