import os
import sys
import requests
import django
import humanize
from discord_slash.context import ComponentContext
import discord
from asgiref.sync import sync_to_async
from discord_slash import SlashCommand
from discord_slash.utils.manage_commands import create_option
from discord_slash.utils.manage_components import create_button, create_actionrow
from discord_slash.model import ButtonStyle
from datetime import datetime


# Django Setup on bot
sys.path.append(os.getcwd() + '/API')
DJANGO_DIRECTORY = os.getcwd() + '/API'
os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.environ["DJANGO_SETTINGS_MODULE"])
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

from django.conf import settings
from django.db.models import Q, F
from core.models.users import UserTransactionHistory
from escrow.models.escrow import Escrow
from escrow.models.trade_offers import TradeOffer
from core.models.transactions import Transaction
from core.models.wallets import ThenewbostonWallet
from core.utils.scan_chain import match_transaction, check_confirmation, scan_chain
from core.utils.send_tnbc import estimate_fee, withdraw_tnbc
from core.models.statistics import Statistic
from core.utils.shortcuts import get_or_create_tnbc_wallet, get_or_create_discord_user

# Environment Variables
TOKEN = os.environ['CROW_DISCORD_TOKEN']

# Initialize the Slash commands
client = discord.Client(intents=discord.Intents.all())
slash = SlashCommand(client, sync_commands=True)


@client.event
async def on_ready():
    print("------------------------------------")
    print("tnbCrow Bot Running:")
    print("------------------------------------")
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="/help"))


@slash.slash(name="rate", description="Last trade rate of TNBC.")
async def rate(ctx):

    await ctx.defer()

    # Gets the last trade rate through tnbcrow API
    r = requests.get('https://tnbcrow.pythonanywhere.com/statistics').json()

    # parse the rate to decimal since the rates are 10^4 of the actual rate
    last_rate = int(r["results"][0]["last_rate"]) / 10000

    embed = discord.Embed()
    embed.add_field(name=f"Last Trade Rate: ${last_rate}", value="Use /trades to check recent verified trades.")
    await ctx.send(embed=embed)


@slash.slash(name="trades", description="Recent trades.")
async def trades(ctx):

    await ctx.defer(hidden=True)

    # gets the recent trades using the tnbcrow API
    r = requests.get('https://tnbcrow.pythonanywhere.com/recent-trades').json()

    trades = r["results"]

    embed = discord.Embed(title="tnbCrow recent OTC trades.")

    for trade in trades:
        humanized_amount = humanize.intcomma(trade['amount'])
        transaction_time = datetime.strptime(trade['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        humanized_date = humanize.naturaltime(transaction_time)
        embed.add_field(name="\u200b", value=f"{humanized_amount} TNBC at ${trade['rate']/10000} - {humanized_date}", inline=False)

    await ctx.send(embed=embed, hidden=True)


@slash.slash(name="help", description="Crow Bot help.")
async def help(ctx):

    await ctx.defer(hidden=True)

    embed=discord.Embed(title="Getting Started to crow discord bot.", url="https://bot.tnbcrow.com/", description="Command List", color=0xe81111)
    embed.add_field(name="Check Balance", value="/balance")
    embed.add_field(name="Deposit TNBC", value="/deposit tnbc")
    embed.add_field(name="Withdraw TNBC", value="/withdraw tnbc")
    embed.add_field(name="Create an escrow", value="/escrow new amount: AMOUNT user: DISCORD_USER", inline=False)
    embed.add_field(name="Check escrow status", value="/escrow status escrow_id: ESCROW_ID")
    embed.add_field(name="List all active escrow", value="/escrow all", inline=False)
    embed.add_field(name="Release the escrow", value="/escrow release escrow_id: ESCROW_ID", inline=False)
    embed.add_field(name="Cancel the escrow", value="/escrow cancel escrow_id: ESCROW_ID")
    embed.add_field(name="Dispute the escrow", value="/escrow dispute escrow_id: ESCROW_ID", inline=False)
    embed.add_field(name="List all completed escrows", value="/escrow history escrow_id: ESCROW_ID", inline=False)
    embed.add_field(name="Last Trade Rate", value="/rate")
    embed.add_field(name="TNBC Price Statistics", value="/stats")

    await ctx.send(embed=embed, hidden=True)


@slash.slash(name="stats", description="TNBC Price Statistics.")
async def stats(ctx):

    await ctx.defer()

    # get the total circulating supply through tnb-analytics github
    r1 = requests.get("https://raw.githubusercontent.com/itsnikhil/tnb-analysis/master/web/js/static.json").json()
    circulating_supply = r1["Total"]
    humanized_supply = humanize.intcomma(circulating_supply)

    # get the last trade rate using tnbcrow API
    r2 = requests.get('https://tnbcrow.pythonanywhere.com/statistics').json()
    last_rate = int(r2["results"][0]["last_rate"]) / 10000

    # calculate the market cap
    market_cap = int(circulating_supply * last_rate)
    humanized_cap = humanize.intcomma(market_cap)

    # create an embed and show it to users
    embed = discord.Embed(title="TNBC Price Statistics")
    embed.add_field(name="Circulating Supply", value=humanized_supply, inline=False)
    embed.add_field(name="Last Trade Rate", value=f"${last_rate}", inline=False)
    embed.add_field(name="Market Cap", value=f"${humanized_cap}", inline=False)
    await ctx.send(embed=embed)


@client.event
async def on_message(message):
    # ignore bot's own message
    if message.author.id == client.user.id:
        return

    discord_user = get_or_create_discord_user(message.author.id)

    # Delete old messages by the user in #trade channel
    if message.channel.id == int(settings.TRADE_CHANNEL_ID):
        async for oldMessage in message.channel.history():
            if oldMessage.author == message.author and oldMessage.id != message.id:
                await oldMessage.delete()
                TradeOffer.objects.filter(user=discord_user).delete()

        TradeOffer.objects.create(user=discord_user, message=message.content, discord_username=message.author)


@slash.slash(name="balance", description="Check User Balance.")
async def user_balance(ctx):

    await ctx.defer(hidden=True)

    discord_user = get_or_create_discord_user(ctx.author.id)
    tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

    embed = discord.Embed()
    embed.add_field(name='Withdrawal Address', value=tnbc_wallet.withdrawal_address, inline=False)
    embed.add_field(name='Balance', value=tnbc_wallet.get_int_balance())
    embed.add_field(name='Locked Amount', value=tnbc_wallet.get_int_locked())
    embed.add_field(name='Available Balance', value=tnbc_wallet.get_int_available_balance())

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="deposit", name="tnbc", description="Deposit TNBC into your crow account.")
async def user_deposit(ctx):

    await ctx.defer(hidden=True)

    discord_user = get_or_create_discord_user(ctx.author.id)
    tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

    qr_data = f"{{'address':{settings.ACCOUNT_NUMBER},'memo':'{tnbc_wallet.memo}'}}"

    embed = discord.Embed(title="Send TNBC to the address with memo.")
    embed.add_field(name='Address', value=settings.ACCOUNT_NUMBER, inline=False)
    embed.add_field(name='MEMO (MEMO is required, or you will lose your coins)', value=tnbc_wallet.memo, inline=False)
    embed.set_image(url=f"https://chart.googleapis.com/chart?chs=150x150&cht=qr&chl={qr_data}")
    embed.set_footer(text="Or, scan the QR code using Keysign Mobile App.")

    await ctx.send(embed=embed, hidden=True, components=[create_actionrow(create_button(custom_id="chain_scan", style=ButtonStyle.green, label="Sent? Scan Chain"))])


@slash.component_callback()
async def chain_scan(ctx: ComponentContext):

    await ctx.defer(hidden=True)

    scan_chain()

    # check_confirmation()

    match_transaction()

    discord_user = get_or_create_discord_user(ctx.author.id)
    tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

    embed = discord.Embed(title="Scan Completed")
    embed.add_field(name='New Balance', value=tnbc_wallet.get_int_balance())
    embed.add_field(name='Locked Amount', value=tnbc_wallet.get_int_locked())
    embed.add_field(name='Available Balance', value=tnbc_wallet.get_int_available_balance())

    await ctx.send(embed=embed, hidden=True, components=[create_actionrow(create_button(custom_id="chain_scan", style=ButtonStyle.green, label="Scan Again?"))])


@slash.subcommand(base="set_withdrawal_address",
                  name="tnbc",
                  description="Set new withdrawal address.",
                  options=[
                      create_option(
                          name="address",
                          description="Enter your withdrawal address.",
                          option_type=3,
                          required=True
                      )
                  ]
                  )
async def user_setwithdrawaladdress(ctx, address: str):

    await ctx.defer(hidden=True)

    discord_user = get_or_create_discord_user(ctx.author.id)
    tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

    if len(address) == 64:
        if address not in settings.PROHIBITED_ACCOUNT_NUMBERS:
            tnbc_wallet.withdrawal_address = address
            tnbc_wallet.save()
            embed = discord.Embed()
            embed.add_field(name='Success', value=f"Successfully set `{address}` as your withdrawal address.")
        else:
            embed = discord.Embed()
            embed.add_field(name='Error!', value="You can not set this account number as your withdrawal address.")
    else:
        embed = discord.Embed()
        embed.add_field(name='Error!', value="Please enter a valid TNBC account number.")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="withdraw", name="tnbc", description="Withdraw TNBC into your account.",
                  options=[
                      create_option(
                          name="amount",
                          description="Enter the amount to withdraw.",
                          option_type=4,
                          required=True
                      )
                  ]
                  )
async def user_withdraw(ctx, amount: int):

    await ctx.defer(hidden=True)

    discord_user = get_or_create_discord_user(ctx.author.id)
    tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

    if tnbc_wallet.withdrawal_address:

        response, fee = estimate_fee()

        if response:
            if not amount < 1:
                if tnbc_wallet.get_int_available_balance() < amount + fee:
                    embed = discord.Embed(title="Inadequate Funds!",
                                          description=f"You only have {tnbc_wallet.get_int_available_balance() - fee} withdrawable TNBC (network fees included) available. \n Use `/deposit tnbc` to deposit TNBC.")

                else:
                    block_response, fee = withdraw_tnbc(tnbc_wallet.withdrawal_address, amount, tnbc_wallet.memo)

                    if block_response:
                        if block_response.status_code == 201:
                            txs = Transaction.objects.create(confirmation_status=Transaction.WAITING_CONFIRMATION,
                                                             transaction_status=Transaction.IDENTIFIED,
                                                             direction=Transaction.OUTGOING,
                                                             account_number=tnbc_wallet.withdrawal_address,
                                                             amount=amount * 100000000,
                                                             fee=fee * 100000000,
                                                             signature=block_response.json()['signature'],
                                                             block=block_response.json()['id'],
                                                             memo=tnbc_wallet.memo)
                            converted_amount_plus_fee =  (amount + fee) * 100000000
                            tnbc_wallet.balance -= converted_amount_plus_fee
                            tnbc_wallet.save()
                            UserTransactionHistory.objects.create(user=discord_user, amount=converted_amount_plus_fee, type=UserTransactionHistory.WITHDRAW, transaction=txs)
                            statistic, created = Statistic.objects.get_or_create(title="main")
                            statistic.total_balance -= converted_amount_plus_fee
                            statistic.save()
                            embed = discord.Embed(title="Coins Withdrawn.",
                                                  description=f"Successfully withdrawn {amount} TNBC to {tnbc_wallet.withdrawal_address} \n Use `/balance` to check your new balance.")
                        else:
                            embed = discord.Embed(title="Error!", description="Please try again later.")
                    else:
                        embed = discord.Embed(title="Error!", description="Can not send transaction block to the bank, Try Again.")
            else:
                embed = discord.Embed(title="Error!", description="You cannot withdraw less than 1 TNBC.")
        else:
            embed = discord.Embed(title="Error!", description="Could not load fee info from the bank.")
    else:
        embed = discord.Embed(title="No withdrawal address set!", description="Use `/set_withdrawal_address` to set withdrawal address.")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="transactions", name="tnbc", description="Check Transaction History.")
async def user_transactions(ctx):

    await ctx.defer(hidden=True)

    discord_user = get_or_create_discord_user(ctx.author.id)

    transactions = (await sync_to_async(UserTransactionHistory.objects.filter)(user=discord_user)).order_by('-created_at')[:8]

    embed = discord.Embed(title="Transaction History", description="")

    for txs in transactions:

        natural_day = humanize.naturalday(txs.created_at)

        embed.add_field(name='\u200b', value=f"{txs.type} - {txs.get_int_amount()} TNBC - {natural_day}", inline=False)

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="escrow",
                  name="new",
                  description="Escrow TNBC with another user.",
                  options=[
                      create_option(
                          name="amount",
                          description="Enter TNBC amount you want to escrow.",
                          option_type=4,
                          required=True
                      ),
                      create_option(
                          name="user",
                          description="Enter your escrow partner.",
                          option_type=6,
                          required=True
                      )
                  ]
                  )
async def escrow_new(ctx, amount: int, user):

    await ctx.defer(hidden=True)

    initiator_discord_user = get_or_create_discord_user(ctx.author.id)
    initiator_tnbc_wallet = get_or_create_tnbc_wallet(initiator_discord_user)

    successor_discord_user = get_or_create_discord_user(user.id)

    if initiator_discord_user != successor_discord_user:

        if amount < settings.MIN_TNBC_ALLOWED:
            embed = discord.Embed(title="Error!", description=f"You can only escrow more than {settings.MIN_TNBC_ALLOWED} TNBC.")

        else:

            if initiator_tnbc_wallet.get_int_available_balance() < amount:
                embed = discord.Embed(title="Inadequate Funds!",
                                      description=f"You only have {initiator_tnbc_wallet.get_int_available_balance()} TNBC available. \n Use `/deposit tnbc` to deposit TNBC!!")
            else:
                integer_fee = amount - int(amount * (100 - settings.CROW_BOT_FEE) / 100)
                database_fee = integer_fee * 100000000
                database_amount = amount * 100000000
                escrow_obj = await sync_to_async(Escrow.objects.create)(amount=database_amount, initiator=initiator_discord_user, successor=successor_discord_user, status=Escrow.OPEN, fee=database_fee)
                initiator_tnbc_wallet.locked += database_amount
                initiator_tnbc_wallet.save()
                embed = discord.Embed(title="Success.", description="")
                embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
                embed.add_field(name='Amount', value=f"{amount}")
                embed.add_field(name='Fee', value=f"{integer_fee}")
                embed.add_field(name='Initiator', value=f"{ctx.author.mention}")
                embed.add_field(name='Successor', value=f"{user.mention}")
                embed.add_field(name='Status', value=f"{escrow_obj.status}", inline=False)
    else:
        embed = discord.Embed(title="Error!", description="You can not escrow yourself tnbc.")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="escrow",
                  name="status",
                  description="Escrow TNBC with another user.",
                  options=[
                      create_option(
                          name="escrow_id",
                          description="Enter escrow id you want to check the status of.",
                          option_type=3,
                          required=True
                      )
                  ]
                  )
async def escrow_status(ctx, escrow_id: str):

    await ctx.defer(hidden=True)

    discord_user = get_or_create_discord_user(ctx.author.id)

    if Escrow.objects.filter(Q(initiator=discord_user) | Q(successor=discord_user), Q(uuid_hex=escrow_id)).exists():
        escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

        initiator = await client.fetch_user(int(escrow_obj.initiator.discord_id))
        successor = await client.fetch_user(int(escrow_obj.successor.discord_id))

        embed = discord.Embed()
        embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
        embed.add_field(name='Amount', value=f"{escrow_obj.get_int_amount()}")
        embed.add_field(name='Fee', value=f"{escrow_obj.get_int_fee()}")
        embed.add_field(name='Initiator', value=f"{initiator.mention}")
        embed.add_field(name='Successor', value=f"{successor.mention}")
        embed.add_field(name='Status', value=f"{escrow_obj.status}")

        if escrow_obj.status == Escrow.ADMIN_SETTLED or escrow_obj.status == Escrow.ADMIN_CANCELLED:
            embed.add_field(name='Settled Towards', value=f"{escrow_obj.settled_towards}")
            embed.add_field(name='Remarks', value=f"{escrow_obj.remarks}", inline=False)
        else:
            embed.add_field(name='Initiator Cancelled', value=f"{escrow_obj.initiator_cancelled}")
            embed.add_field(name='Successor Cancelled', value=f"{escrow_obj.successor_cancelled}")

    else:
        embed = discord.Embed(title="Error!", description="404 Not Found.")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="escrow", name="all", description="All your active escrows.")
async def escrow_all(ctx):

    await ctx.defer(hidden=True)

    discord_user = get_or_create_discord_user(ctx.author.id)

    if Escrow.objects.filter(Q(initiator=discord_user) | Q(successor=discord_user), Q(status=Escrow.OPEN) | Q(status=Escrow.DISPUTE)).exists():
        escrows = await sync_to_async(Escrow.objects.filter)(Q(initiator=discord_user) | Q(successor=discord_user), Q(status=Escrow.OPEN) | Q(status=Escrow.DISPUTE))

        embed = discord.Embed()

        for escrow in escrows:

            embed.add_field(name='ID', value=f"{escrow.uuid_hex}", inline=False)
            embed.add_field(name='Amount', value=f"{escrow.get_int_amount()}")
            embed.add_field(name='Fee', value=f"{escrow.get_int_fee()}")
            embed.add_field(name='Status', value=f"{escrow.status}")

    else:
        embed = discord.Embed(title="Oops..", description="No active escrows found.")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="escrow", name="history", description="All your recent escrows.")
async def escrow_history(ctx):

    await ctx.defer(hidden=True)

    discord_user = get_or_create_discord_user(ctx.author.id)

    if Escrow.objects.filter(Q(initiator=discord_user) | Q(successor=discord_user)).exists():
        escrows = (await sync_to_async(Escrow.objects.filter)(Q(initiator=discord_user) | Q(successor=discord_user)))[:8]

        embed = discord.Embed()

        for escrow in escrows:

            embed.add_field(name='ID', value=f"{escrow.uuid_hex}", inline=False)
            embed.add_field(name='Amount', value=f"{escrow.get_int_amount()}")
            embed.add_field(name='Fee', value=f"{escrow.get_int_fee()}")
            embed.add_field(name='Status', value=f"{escrow.status}")

    else:
        embed = discord.Embed(title="Oops..", description="You've not complete a single escrow.")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="escrow",
                  name="release",
                  description="Release escrow to successor.",
                  options=[
                      create_option(
                          name="escrow_id",
                          description="Enter escrow id you want to check the status of.",
                          option_type=3,
                          required=True
                      )
                  ]
                  )
async def escrow_release(ctx, escrow_id: str):

    await ctx.defer(hidden=True)

    discord_user = get_or_create_discord_user(ctx.author.id)

    if Escrow.objects.filter(uuid_hex=escrow_id, initiator=discord_user).exists():

        escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

        if escrow_obj.status == Escrow.OPEN:

            escrow_obj.status = Escrow.COMPLETED
            ThenewbostonWallet.objects.filter(user=discord_user).update(balance=F('balance') - escrow_obj.amount, locked=F('locked') - escrow_obj.amount)
            ThenewbostonWallet.objects.filter(user=escrow_obj.successor).update(balance=F('balance') + escrow_obj.amount - escrow_obj.fee)
            escrow_obj.save()

            embed = discord.Embed(title="Success", description="")
            embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
            embed.add_field(name='Amount', value=f"{escrow_obj.get_int_amount()}")
            embed.add_field(name='Fee', value=f"{escrow_obj.get_int_fee()}")
            embed.add_field(name='Status', value=f"{escrow_obj.status}")

        else:
            embed = discord.Embed(title="Error!", description=f"You cannot release the escrow of status {escrow_obj.status}.")
    else:
        embed = discord.Embed(title="Error!", description="You do not have permission to perform the action.")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="escrow",
                  name="cancel",
                  description="Cancel escrow.",
                  options=[
                      create_option(
                          name="escrow_id",
                          description="Enter escrow id you want to check the status of.",
                          option_type=3,
                          required=True
                      )
                  ]
                  )
async def escrow_cancel(ctx, escrow_id: str):

    await ctx.defer(hidden=True)

    discord_user = get_or_create_discord_user(ctx.author.id)

    # Check if the user is initiator or successor
    if Escrow.objects.filter(Q(initiator=discord_user) |
                             Q(successor=discord_user),
                             Q(uuid_hex=escrow_id)).exists():

        escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

        if escrow_obj.status == Escrow.OPEN:

            if int(escrow_obj.initiator.discord_id) == ctx.author.id:
                escrow_obj.initiator_cancelled = True
                if escrow_obj.successor_cancelled is True:
                    escrow_obj.status = Escrow.CANCELLED
                    ThenewbostonWallet.objects.filter(user=escrow_obj.initiator).update(locked=F('locked') - escrow_obj.amount)
            else:
                escrow_obj.successor_cancelled = True
                if escrow_obj.initiator_cancelled is True:
                    escrow_obj.status = Escrow.CANCELLED
                    ThenewbostonWallet.objects.filter(user=escrow_obj.initiator).update(locked=F('locked') - escrow_obj.amount)

            escrow_obj.save()

            embed = discord.Embed(title="Success", description="")
            embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
            embed.add_field(name='Amount', value=f"{escrow_obj.get_int_amount()}")
            embed.add_field(name='Fee', value=f"{escrow_obj.get_int_fee()}")
            embed.add_field(name='Status', value=f"{escrow_obj.status}")
            embed.add_field(name='Initiator Cancelled', value=f"{escrow_obj.initiator_cancelled}", inline=False)
            embed.add_field(name='Successor Cancelled', value=f"{escrow_obj.successor_cancelled}")
        else:
            embed = discord.Embed(title="Error!", description=f"You cannot cancel the escrow of status {escrow_obj.status}.")

    else:
        embed = discord.Embed(title="Error!", description="404 Not Found.")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="escrow",
                  name="dispute",
                  description="Start an dispute.",
                  options=[
                      create_option(
                          name="escrow_id",
                          description="Enter escrow id you want to check the status of.",
                          option_type=3,
                          required=True
                      )
                  ]
                  )
async def escrow_dispute(ctx, escrow_id: str):

    await ctx.defer(hidden=True)

    discord_user = get_or_create_discord_user(ctx.author.id)

    if Escrow.objects.filter(Q(initiator=discord_user) |
                             Q(successor=discord_user),
                             Q(uuid_hex=escrow_id)).exists():

        escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

        if escrow_obj.status == Escrow.OPEN:
            escrow_obj.status = Escrow.DISPUTE
            escrow_obj.save()

            dispute = client.get_channel(int(settings.DISPUTE_CHANNEL_ID))

            initiator = await client.fetch_user(int(escrow_obj.initiator.discord_id))
            successor = await client.fetch_user(int(escrow_obj.successor.discord_id))

            dispute_embed = discord.Embed(title="Dispute Alert!", description="")
            dispute_embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
            dispute_embed.add_field(name='Amount', value=f"{escrow_obj.amount}")
            dispute_embed.add_field(name='Initiator', value=f"{initiator}")
            dispute_embed.add_field(name='Successor', value=f"{successor}")
            dispute = await dispute.send(embed=dispute_embed)

            await dispute.add_reaction("👀")
            await dispute.add_reaction("✅")

            embed = discord.Embed(title="Success", description="Agent will create a private channel within this server to resolve dispute. **Agent will never DM you!!**")
            embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
            embed.add_field(name='Amount', value=f"{escrow_obj.get_int_amount()}")
            embed.add_field(name='Fee', value=f"{escrow_obj.get_int_fee()}")
            embed.add_field(name='Initiator', value=f"{initiator.mention}")
            embed.add_field(name='Successor', value=f"{successor.mention}")
            embed.add_field(name='Status', value=f"{escrow_obj.status}")
        else:
            embed = discord.Embed(title="Error!", description=f"You cannot dispute the escrow of status {escrow_obj.status}.")

    else:
        embed = discord.Embed(title="Error!", description="404 Not Found.")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="agent",
                  name="cancel",
                  description="Cancel escrow.",
                  options=[
                      create_option(
                          name="escrow_id",
                          description="Enter escrow id you want to cancel.",
                          option_type=3,
                          required=True
                      ),
                      create_option(
                          name="remarks",
                          description="Summary of the escrow.",
                          option_type=3,
                          required=True
                      )
                  ]
                  )
async def agent_cancel(ctx, escrow_id: str, remarks: str):

    await ctx.defer(hidden=True)

    if int(settings.AGENT_ROLE_ID) in [y.id for y in ctx.author.roles]:
        if Escrow.objects.filter(uuid_hex=escrow_id).exists():

            escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

            discord_user = get_or_create_discord_user(ctx.author.id)

            if escrow_obj.status == Escrow.DISPUTE:
                escrow_obj.status = Escrow.ADMIN_CANCELLED
                escrow_obj.remarks = remarks
                escrow_obj.agent = discord_user
                ThenewbostonWallet.objects.filter(user=escrow_obj.initiator).update(locked=F('locked') - escrow_obj.amount)
                escrow_obj.save()

                embed = discord.Embed(title="Success", description="")
                embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
                embed.add_field(name='Amount', value=f"{escrow_obj.get_int_amount()}")
                embed.add_field(name='Fee', value=f"{escrow_obj.get_int_fee()}")
                embed.add_field(name='Status', value=f"{escrow_obj.status}")
            else:
                embed = discord.Embed(title="Error!", description=f"You cannot cancel the escrow of status {escrow_obj.status}.")
        else:
            embed = discord.Embed(title="Error!", description="404 Not Found.")
    else:
        embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="agent",
                  name="release",
                  description="Cancel escrow!",
                  options=[
                      create_option(
                          name="escrow_id",
                          description="Enter escrow id you want to cancel.",
                          option_type=3,
                          required=True
                      ),
                      create_option(
                          name="user",
                          description="Enter user to release the funds to.",
                          option_type=6,
                          required=True
                      ),
                      create_option(
                          name="remarks",
                          description="Summary of the dispute.",
                          option_type=3,
                          required=True
                      )
                  ]
                  )
async def agent_release(ctx, escrow_id: str, user, remarks: str):

    await ctx.defer(hidden=True)

    if int(settings.AGENT_ROLE_ID) in [y.id for y in ctx.author.roles]:

        if Escrow.objects.filter(Q(uuid_hex=escrow_id),
                                 Q(status=Escrow.DISPUTE),
                                 Q(initiator__discord_id=str(user.id)) | Q(successor__discord_id=str(user.id))).exists():

            escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)
            discord_user = get_or_create_discord_user(ctx.author.id)
            escrow_obj.status = Escrow.ADMIN_SETTLED
            escrow_obj.agent = discord_user
            escrow_obj.remarks = remarks

            if user.id == str(escrow_obj.initiator.discord_id):
                ThenewbostonWallet.objects.filter(user=escrow_obj.initiator).update(balance=F('balance') - escrow_obj.fee, locked=F('locked') - escrow_obj.amount)
                escrow_obj.settled_towards = Escrow.INITIATOR
                escrow_obj.save()
            else:
                ThenewbostonWallet.objects.filter(user=escrow_obj.initiator).update(balance=F('balance') - escrow_obj.amount, locked=F('locked') - escrow_obj.amount)
                ThenewbostonWallet.objects.filter(user=escrow_obj.successor).update(balance=F('balance') + escrow_obj.amount - escrow_obj.fee)
                escrow_obj.save()

            embed = discord.Embed(title="Success", description="")
            embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
            embed.add_field(name='Amount', value=f"{escrow_obj.get_int_amount()}")
            embed.add_field(name='Fee', value=f"{escrow_obj.get_int_fee()}")
            embed.add_field(name='Status', value=f"{escrow_obj.status}")
            embed.add_field(name='Remarks', value=f"{escrow_obj.remarks}", inline=False)

        else:
            embed = discord.Embed(title="Error!", description="Disputed escrow not found or the user does not exist for the escrow.")
    else:
        embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.")

    await ctx.send(embed=embed, hidden=True)


@slash.slash(name="kill", description="Kill the bot!")
async def kill(ctx):

    await ctx.defer(hidden=True)

    if int(ctx.author.id) == int(settings.BOT_MANAGER_ID):
        print("Shutting Down the bot")
        await ctx.send("Bot Shut Down", hidden=True)
        await client.close()
    else:
        embed = discord.Embed(title="Nope", description="")
        embed.set_image(url="https://i.ibb.co/zQc3xDp/download-min-1.png")
        await ctx.send(embed=embed, hidden=True)

client.run(TOKEN)
