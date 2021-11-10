from rest_framework import mixins, viewsets

from ..models.profile import Profile
from ..serializers.profile import ProfileSerializer


class ProfileViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
