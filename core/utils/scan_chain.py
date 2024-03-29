import requests
import os
from datetime import datetime, timedelta

from django.utils import timezone
from django.conf import settings

from ..models.scan_tracker import ScanTracker
from ..models.transactions import Transaction
from ..models.statistics import Statistic
from ..models.users import UserTransactionHistory
from ..models.wallets import ThenewbostonWallet


def check_confirmation():

    waiting_confirmations_txs = Transaction.objects.filter(confirmation_status=Transaction.WAITING_CONFIRMATION,
                                                           created_at__gt=timezone.now() - timedelta(hours=1))

    for txs in waiting_confirmations_txs:

        try:
            r = requests.get(f"http://{settings.BANK_IP}/confirmation_blocks?block__signature={txs.signature}").json()

        except requests.exceptions.RequestException:
            return False

        if 'count' in r:
            if int(r['count']) > 0:
                txs.total_confirmations = 1
                txs.confirmation_status = Transaction.CONFIRMED
                txs.save()

                if txs.direction == Transaction.INCOMING:

                    lower_case_memo = txs.memo.lower()

                    if lower_case_memo != "internal":
                        statistics, created = Statistic.objects.get_or_create(title="main")
                        statistics.total_balance += txs.amount
                        statistics.save()
                else:
                    statistics, created = Statistic.objects.get_or_create(title="main")
                    statistics.total_balance -= txs.amount - settings.TNBC_TRANSACTION_FEE
                    statistics.save()


def scan_chain():

    scan_tracker, created = ScanTracker.objects.get_or_create(title="main")

    TNBC_TRANSACTION_SCAN_URL = f"http://{settings.BANK_IP}/bank_transactions?account_number={settings.TNBCROW_BOT_ACCOUNT_NUMBER}&block__sender=&fee=&recipient="

    next_url = TNBC_TRANSACTION_SCAN_URL

    transaction_fee = 0

    while next_url:

        try:
            r = requests.get(next_url).json()

        except requests.exceptions.RequestException:
            return False

        next_url = r['next']

        for transaction in r['results']:

            transaction_time = timezone.make_aware(datetime.strptime(transaction['block']['created_date'], '%Y-%m-%dT%H:%M:%S.%fZ'))
            transaction_exists = Transaction.objects.filter(signature=transaction['block']['signature']).exists()

            if scan_tracker.last_scanned < transaction_time and not transaction_exists:

                amount = int(transaction['amount']) * settings.TNBC_MULTIPLICATION_FACTOR

                if transaction['recipient'] == settings.TNBCROW_BOT_ACCOUNT_NUMBER:
                    direction = Transaction.INCOMING
                    account_number = transaction['block']['sender']
                else:
                    transaction_fee = settings.TNBC_TRANSACTION_FEE
                    direction = Transaction.OUTGOING
                    account_number = transaction['recipient']

                if transaction['fee'] == "":
                    Transaction.objects.create(confirmation_status=Transaction.WAITING_CONFIRMATION,
                                               direction=direction,
                                               transaction_status=Transaction.NEW,
                                               account_number=account_number,
                                               amount=amount,
                                               fee=transaction_fee,
                                               block=transaction['block']['id'],
                                               signature=transaction['block']['signature'],
                                               memo=transaction['memo'])

            else:
                next_url = None
                break

    scan_tracker.total_scans += 1
    scan_tracker.save()


def match_transaction():

    if os.environ['CHECK_TNBC_CONFIRMATION'] == 'True':
        confirmed_txs = Transaction.objects.filter(confirmation_status=Transaction.CONFIRMED,
                                                   transaction_status=Transaction.NEW,
                                                   direction=Transaction.INCOMING)
    else:
        confirmed_txs = Transaction.objects.filter(confirmation_status=Transaction.WAITING_CONFIRMATION,
                                                   transaction_status=Transaction.NEW,
                                                   direction=Transaction.INCOMING)

    for txs in confirmed_txs:

        lower_case_memo = txs.memo.lower()

        if lower_case_memo == "internal":
            txs.transaction_status = Transaction.IDENTIFIED
            txs.save()

        elif ThenewbostonWallet.objects.filter(memo=txs.memo).exists():

            wallet = ThenewbostonWallet.objects.get(memo=txs.memo)
            wallet.balance += txs.amount
            wallet.save()

            UserTransactionHistory.objects.create(user=wallet.user, amount=txs.amount, type=UserTransactionHistory.DEPOSIT, transaction=txs)

            txs.transaction_status = Transaction.IDENTIFIED
            txs.save()

        else:
            txs.transaction_status = Transaction.UNIDENTIFIED
            txs.save()
