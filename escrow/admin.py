from django.contrib import admin

from .models.escrow import Escrow
from .models.profile import Profile
from .models.trade_offers import TradeOffer


admin.site.register(Escrow)
admin.site.register(Profile)
admin.site.register(TradeOffer)
