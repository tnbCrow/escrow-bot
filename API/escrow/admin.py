from django.contrib import admin

from .models.escrow import Escrow
from .models.transaction import Transaction
from .models.user import User
from .models.scan_tracker import ScanTracker
from .models.statistic import Statistic
from .models.agent import Agent

# Register your models here.
admin.site.register(Escrow)
admin.site.register(Transaction)
admin.site.register(User)
admin.site.register(ScanTracker)
admin.site.register(Statistic)
admin.site.register(Agent)
