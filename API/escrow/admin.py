from django.contrib import admin

from .models.escrow import Escrow
from .models.users import EscrowUser
from .models.trade_offers import TradeOffer


admin.site.register(Escrow)
admin.site.register(EscrowUser)
admin.site.register(TradeOffer)
