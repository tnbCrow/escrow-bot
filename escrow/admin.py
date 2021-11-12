from django.contrib import admin

from .models.escrow import Escrow
from .models.profile import Profile


admin.site.register(Escrow)
admin.site.register(Profile)
