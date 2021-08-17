from django.contrib import admin

from .models.escrow import Escrow
from .models.transaction import Transaction
from .models.user import User

# Register your models here.
admin.site.register(Escrow)
admin.site.register(Transaction)
admin.site.register(User)
