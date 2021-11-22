from django.contrib import admin

from .models.transactions import Transaction
from .models.users import User, UserTransactionHistory
from .models.wallets import ThenewbostonWallet
from .models.scan_tracker import ScanTracker
from .models.statistics import Statistic
from .models.bot_config import BotConfig


# Register your models here.
admin.site.register(Transaction)
admin.site.register(User)
admin.site.register(ScanTracker)
admin.site.register(Statistic)
admin.site.register(UserTransactionHistory)
admin.site.register(ThenewbostonWallet)
admin.site.register(BotConfig)
