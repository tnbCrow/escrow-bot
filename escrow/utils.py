from .models.profile import Profile


def get_or_create_user_profile(user):

    obj, created = Profile.objects.get_or_create(user=user)

    return obj
