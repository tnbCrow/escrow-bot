from django.contrib import admin

from .models.escrow import Escrow
from .models.profile import Profile
from .models.advertisement import Advertisement
from .models.payment_method import PaymentMethod


admin.site.register(Escrow)
admin.site.register(Profile)
admin.site.register(Advertisement)
admin.site.register(PaymentMethod)
