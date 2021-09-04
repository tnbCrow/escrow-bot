from django.contrib import admin

from .models.escrow import Escrow
from .models.users import EscrowUser


admin.site.register(Escrow)
admin.site.register(EscrowUser)
