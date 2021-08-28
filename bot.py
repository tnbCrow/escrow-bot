import os
import sys
import requests
import django
import humanize
import discord
from asgiref.sync import sync_to_async
from discord.ext import commands
from discord_slash import SlashCommand
from discord_slash.utils.manage_commands import create_option
from datetime import datetime

# Django Setup on bot
sys.path.append(os.getcwd() + '/API')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()
from django.conf import settings
from django.db.models import Q
from escrow.models.user import User
from escrow.models.escrow import Escrow
from escrow.models.transaction import Transaction, UserTransactionHistory
from escrow.utils.scan_chain import match_transaction
from escrow.utils.send_tnbc import estimate_fee, withdraw_tnbc

# Environment Variables
TOKEN = os.environ.get('CROW_DISCORD_TOKEN')

# Initialize the Slash commands
client = discord.Client(intents=discord.Intents.all())
slash = SlashCommand(client, sync_commands=True)


@client.event
async def on_ready():
    print("------------------------------------")
    print("tnbCrow Bot Running:")
    print("------------------------------------")
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="TNBC grow"))


@slash.slash(name="rate", description="Last trade rate of TNBC.")
async def rate(ctx):
    # Gets the last trade rate through tnbcrow API
    r = requests.get('https://tnbcrow.pythonanywhere.com/statistics').json()

    # parse the rate to decimal since the rates are 10^4 of the actual rate
    last_rate = int(r["results"][0]["last_rate"]) / 10000

    embed = discord.Embed()
    embed.add_field(name=f"Last Trade Rate: ${last_rate}", value="Use /trades to check recent verified trades!!")
    await ctx.send(embed=embed)


@slash.slash(name="trades", description="Recent trades!!")
async def trades(ctx):
    # gets the recent trades using the tnbcrow API
    r = requests.get('https://tnbcrow.pythonanywhere.com/recent-trades').json()

    trades = r["results"]

    embed = discord.Embed(title="tnbCrow recent OTC trades!!")

    for trade in trades:
        humanized_amount = humanize.intcomma(trade['amount'])
        transaction_time = datetime.strptime(trade['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        humanized_date = humanize.naturaltime(transaction_time)
        embed.add_field(name="\u200b", value=f"{humanized_amount} TNBC at ${trade['rate']/10000} - {humanized_date}", inline=False)

    await ctx.send(embed=embed, hidden=True)


@slash.slash(name="help", description="Crow Bot help!!")
async def help(ctx):
    embed = discord.Embed(title="Commands", color=discord.Color.blue())
    embed.add_field(name="/rate", value="Last verified trade of TNBC!!", inline=False)
    embed.add_field(name="/trades", value="Recent verified trades!!", inline=False)
    embed.add_field(name="/stats", value="TNBC Price Statistics!!", inline=False)
    await ctx.send(embed=embed, hidden=True)


@slash.slash(name="stats", description="TNBC Price Statistics!!")
async def stats(ctx):
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

    # Delete old messages by the user in #trade channel
    if message.channel.id == int(settings.TRADE_CHANNEL_ID):
        async for oldMessage in message.channel.history():
            if oldMessage.author == message.author and oldMessage.id != message.id:
                await oldMessage.delete()


@slash.subcommand(base="user", name="balance", description="Check User Balance!!")
async def user_balance(ctx):

    match_transaction()

    obj, created = await sync_to_async(User.objects.get_or_create)(discord_id=ctx.author.id)

    embed = discord.Embed()
    embed.add_field(name='Withdrawal Address', value=obj.withdrawal_address, inline=False)
    embed.add_field(name='Balance', value=obj.balance)
    embed.add_field(name='Locked Amount', value=obj.locked)
    embed.add_field(name='Available Balance', value=obj.get_available_balance())

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="user", name="deposit", description="Deposit TNBC into your crow account!!")
async def user_deposit(ctx):

    obj, created = await sync_to_async(User.objects.get_or_create)(discord_id=ctx.author.id)

    embed = discord.Embed(title="Send TNBC to the address with memo!!")
    embed.add_field(name='Address', value=settings.ACCOUNT_NUMBER, inline=False)
    embed.add_field(name='MEMO (MEMO is required, or you will lose your coins)', value=obj.memo, inline=False)
    embed.add_field(name="Sent?", value="Use `/user_balance` command to check the deposit!!")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="user",
             name="set_withdrawal_address",
             description="Set new withdrawal address!!",
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

    obj, created = await sync_to_async(User.objects.get_or_create)(discord_id=ctx.author.id)

    if len(address) == 64:
        if not address in settings.PROHIBITED_ACCOUNT_NUMBERS:
            obj.withdrawal_address = address
            obj.save()
            embed = discord.Embed()
            embed.add_field(name='Success!!', value=f"Successfully set `{address}` as your withdrawal address!!")
        else:
            embed = discord.Embed()
            embed.add_field(name='Error!!', value="You can not set this account number as your withdrawal address!!")
    else:
        embed = discord.Embed()
        embed.add_field(name='Error!!', value="Please enter a valid TNBC account number!!")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="user", 
             name="withdraw",
             description="Withdraw TNBC into your account!!",
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

    obj, created = await sync_to_async(User.objects.get_or_create)(discord_id=ctx.author.id)

    if obj.withdrawal_address:

        fee = estimate_fee()

        if obj.get_available_balance() < amount + fee:
            embed = discord.Embed(title="Inadequate Funds!!",
                                  description=f"You only have {obj.get_available_balance() - fee} withdrawable TNBC (network fees included) available. \n Use `/user_deposit` to deposit TNBC!!")

        else:
            block_response, fee = withdraw_tnbc(obj.withdrawal_address, amount, obj.memo)

            if block_response.status_code == 201:

                Transaction.objects.create(confirmation_status=Transaction.WAITING_CONFIRMATION,
                                           transaction_status=Transaction.IDENTIFIED,
                                           direction=Transaction.OUTGOING,
                                           account_number=obj.withdrawal_address,
                                           amount=amount,
                                           fee=fee,
                                           signature=block_response.json()['signature'],
                                           block=block_response.json()['id'],
                                           memo=obj.memo)
                obj.balance -= amount + fee
                obj.save()
                UserTransactionHistory.objects.create(user=obj, amount=amount + fee, type=UserTransactionHistory.WITHDRAW)
                embed = discord.Embed(title="Coins Withdrawn!",
                                      description=f"Successfully withdrawn {amount} TNBC to {obj.withdrawal_address} \n Use `/user_balance` to check your new balance.")
            else:
                embed = discord.Embed(title="Error!",
                                      description="Please try again later!!")
    else:
        embed = discord.Embed(title="No withdrawal address set!!", description="Use `/user_setwithdrawaladdress` to set withdrawal address!!")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="user", name="transactions", description="Check Transaction History!!")
async def user_transactions(ctx):

    obj, created = await sync_to_async(User.objects.get_or_create)(discord_id=ctx.author.id)

    transactions = (await sync_to_async(UserTransactionHistory.objects.filter)(user=obj)).order_by('-created_at')[:8]

    embed = discord.Embed(title="Transaction History", description="")

    for txs in transactions:

        natural_day = humanize.naturalday(txs.created_at)

        embed.add_field(name='\u200b', value=f"{txs.type} - {txs.amount} TNBC - {natural_day}", inline=False)

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="escrow",
             name="new",
             description="Escrow TNBC with another user!!",
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

    initiator, created = await sync_to_async(User.objects.get_or_create)(discord_id=ctx.author.id)
    successor, created = await sync_to_async(User.objects.get_or_create)(discord_id=user.id)

    if initiator != successor:

        if amount < settings.MIN_TNBC_ALLOWED:
            embed = discord.Embed(title="Error!!", description="You can only escrow more than 100 TNBC.")

        else:

            if initiator.get_available_balance() < amount:
                embed = discord.Embed(title="Inadequate Funds!!",
                                    description=f"You only have {initiator.get_available_balance()} TNBC available. \n Use `/user_deposit` to deposit TNBC!!")
            else:
                escrow_obj = await sync_to_async(Escrow.objects.create)(amount=amount, initiator=initiator, successor=successor, status=Escrow.OPEN)
                initiator.locked += amount
                initiator.save()
                embed = discord.Embed(title="Success!!",
                                    description="")
                embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
                embed.add_field(name='Amount', value=f"{amount}")
                embed.add_field(name='Initiator', value=f"{ctx.author}")
                embed.add_field(name='Successor', value=f"{user}")
                embed.add_field(name='Status', value=f"{escrow_obj.status}", inline=False)
    else:
        embed = discord.Embed(title="Error!!", description="You cannot escrow yourself tnbc.")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="escrow",
             name="status",
             description="Escrow TNBC with another user!!",
             options=[
                 create_option(
                     name="escrow_id",
                     description="Enter escrow id you want to check the status of!",
                     option_type=3,
                     required=True
                 )
             ]
             )
async def escrow_status(ctx, escrow_id: str):

    obj, created = User.objects.get_or_create(discord_id=ctx.author.id)

    if Escrow.objects.filter(Q(initiator=obj) | Q(successor=obj)).exists():
        escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

        initiator = await client.fetch_user(escrow_obj.initiator.discord_id)
        successor = await client.fetch_user(escrow_obj.successor.discord_id)

        embed = discord.Embed(title="Success!!", description="")
        embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
        embed.add_field(name='Amount', value=f"{escrow_obj.amount}")
        embed.add_field(name='Initiator', value=f"{initiator}")
        embed.add_field(name='Successor', value=f"{successor}")
        embed.add_field(name='Status', value=f"{escrow_obj.status}", inline=False)
        embed.add_field(name='Initiator Cancelled', value=f"{escrow_obj.initiator_cancelled}")
        embed.add_field(name='Successor Cancelled', value=f"{escrow_obj.successor_cancelled}")

    else:
        embed = discord.Embed(title="Error!!", description="404 Not Found.")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="escrow", name="all", description="All your active escrows!!")
async def escrow_all(ctx):
    
    obj, created = User.objects.get_or_create(discord_id=ctx.author.id)

    if Escrow.objects.filter(Q(initiator=obj) | Q(successor=obj), Q(status=Escrow.OPEN) | Q(status=Escrow.DISPUTE)).exists():
        escrows = await sync_to_async(Escrow.objects.filter)(Q(initiator=obj) | Q(successor=obj), Q(status=Escrow.OPEN) | Q(status=Escrow.DISPUTE))

        embed = discord.Embed()

        for escrow in escrows:

            embed.add_field(name='ID', value=f"{escrow.uuid_hex}", inline=False)
            embed.add_field(name='Amount', value=f"{escrow.amount}")
            embed.add_field(name='Status', value=f"{escrow.status}")

    else:
        embed = discord.Embed(title="Error!!", description="404 Not Found.")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="escrow", name="history", description="All your recent escrows!!")
async def escrow_history(ctx):

    obj, created = User.objects.get_or_create(discord_id=ctx.author.id)

    if Escrow.objects.filter(Q(initiator=obj) | Q(successor=obj)).exists():
        escrows = (await sync_to_async(Escrow.objects.filter)(Q(initiator=obj) | Q(successor=obj)))[:8]

        embed = discord.Embed()

        for escrow in escrows:

            embed.add_field(name='ID', value=f"{escrow.uuid_hex}", inline=False)
            embed.add_field(name='Amount', value=f"{escrow.amount}")
            embed.add_field(name='Status', value=f"{escrow.status}")

    else:
        embed = discord.Embed(title="Error!!", description="404 Not Found.")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="escrow",
             name="release",
             description="Release escrow to successor!!",
             options=[
                 create_option(
                     name="escrow_id",
                     description="Enter escrow id you want to check the status of!",
                     option_type=3,
                     required=True
                 )
             ]
             )
async def escrow_release(ctx, escrow_id: str):

    obj, created = User.objects.get_or_create(discord_id=ctx.author.id)

    if Escrow.objects.filter(uuid_hex=escrow_id, initiator=obj).exists():

        escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

        if escrow_obj.status == Escrow.OPEN:

            escrow_obj.status = Escrow.COMPLETED
            escrow_obj.initiator.balance -= escrow_obj.amount
            escrow_obj.initiator.locked -= escrow_obj.amount
            escrow_obj.successor.balance += int(escrow_obj.amount * (100 - settings.CROW_BOT_FEE) / 100)
            escrow_obj.save()
            escrow_obj.initiator.save()
            escrow_obj.successor.save()

            embed = discord.Embed(title="Success!!", description="")
            embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
            embed.add_field(name='Amount', value=f"{escrow_obj.amount}")
            embed.add_field(name='Status', value=f"{escrow_obj.status}")

        else:
            embed = discord.Embed(title="Error!!", description=f"You cannot release the escrow of status {escrow_obj.status}.")
    else:
        embed = discord.Embed(title="Error!!", description="You do not have permission to perform the action.")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="escrow",
             name="cancel",
             description="Cancel escrow!!",
             options=[
                 create_option(
                     name="escrow_id",
                     description="Enter escrow id you want to check the status of!",
                     option_type=3,
                     required=True
                 )
             ]
             )
async def escrow_cancel(ctx, escrow_id: str):

    obj, created = User.objects.get_or_create(discord_id=ctx.author.id)

    # Check if the user is initiator or successor
    if Escrow.objects.filter(Q(initiator=obj) |
                             Q(successor=obj),
                             Q(uuid_hex=escrow_id)).exists():

        escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

        if escrow_obj.status == Escrow.OPEN:

            if escrow_obj.initiator.discord_id == ctx.author.id:
                escrow_obj.initiator_cancelled = True
                if escrow_obj.successor_cancelled == True:
                    escrow_obj.status = Escrow.CANCELLED
                    escrow_obj.initiator.locked -= escrow_obj.amount
                    escrow_obj.initiator.save()

            else:
                escrow_obj.successor_cancelled = True
                if escrow_obj.initiator_cancelled == True:
                    escrow_obj.status = Escrow.CANCELLED
                    escrow_obj.initiator.locked -= escrow_obj.amount
                    escrow_obj.initiator.save()

            escrow_obj.save()
    
            embed = discord.Embed(title="Success!!", description="")
            embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
            embed.add_field(name='Amount', value=f"{escrow_obj.amount}")
            embed.add_field(name='Status', value=f"{escrow_obj.status}")
            embed.add_field(name='Initiator Cancelled', value=f"{escrow_obj.initiator_cancelled}", inline=False)
            embed.add_field(name='Successor Cancelled', value=f"{escrow_obj.successor_cancelled}")
        else:
            embed = discord.Embed(title="Error!!", description=f"You cannot cancel the escrow of status {escrow_obj.status}.")

    else:
        embed = discord.Embed(title="Error!!", description="404 Not Found.")


    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="escrow",
             name="dispute",
             description="Start an dispute!!",
             options=[
                 create_option(
                     name="escrow_id",
                     description="Enter escrow id you want to check the status of!",
                     option_type=3,
                     required=True
                 )
             ]
             )
async def escrow_dispute(ctx, escrow_id: str):
    
    obj, created = User.objects.get_or_create(discord_id=ctx.author.id)

    if Escrow.objects.filter(Q(initiator=obj) |
                             Q(successor=obj),
                             Q(uuid_hex=escrow_id)).exists():

        escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

        if escrow_obj.status == Escrow.OPEN:
            escrow_obj.status = Escrow.DISPUTE
            escrow_obj.save()
            
            dispute = client.get_channel(int(settings.DISPUTE_CHANNEL_ID))

            initiator = await client.fetch_user(escrow_obj.initiator.discord_id)
            successor = await client.fetch_user(escrow_obj.successor.discord_id)

            dispute_embed = discord.Embed(title="Dispute Alert!!", description="")
            dispute_embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
            dispute_embed.add_field(name='Amount', value=f"{escrow_obj.amount}")
            dispute_embed.add_field(name='Initiator', value=f"{initiator}")
            dispute_embed.add_field(name='Successor', value=f"{successor}")
            dispute_embed.add_field(name='Status', value=f"{escrow_obj.status}")
            dispute = await dispute.send(embed=dispute_embed)

            await dispute.add_reaction("👀")
            await dispute.add_reaction("✅")

            embed = discord.Embed(title="Success!!", description="")
            embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
            embed.add_field(name='Amount', value=f"{escrow_obj.amount}")
            embed.add_field(name='Initiator', value=f"{initiator}")
            embed.add_field(name='Successor', value=f"{successor}")
            embed.add_field(name='Status', value=f"{escrow_obj.status}")
        else:
            embed = discord.Embed(title="Error!!", description=f"You cannot dispute the escrow of status {escrow_obj.status}.")

    else:
        embed = discord.Embed(title="Error!!", description="404 Not Found.")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="agent",
             name="cancel",
             description="Cancel escrow!!",
             options=[
                 create_option(
                     name="escrow_id",
                     description="Enter escrow id you want to cancel!",
                     option_type=3,
                     required=True
                 )
             ]
             )
async def agent_cancel(ctx, escrow_id: str):

    if int(settings.AGENT_ROLE_ID) in [y.id for y in ctx.author.roles]:
        if Escrow.objects.filter(uuid_hex=escrow_id).exists():

            escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

            if escrow_obj.status == Escrow.DISPUTE:
                escrow_obj.status = Escrow.ADMIN_CANCELLED
                escrow_obj.agent = User.objects.get(discord_id=ctx.author.id)
                escrow_obj.initiator.locked -= escrow_obj.amount
                escrow_obj.initiator.save()
                escrow_obj.save()

                embed = discord.Embed(title="Success!!", description="")
                embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
                embed.add_field(name='Amount', value=f"{escrow_obj.amount}")
                embed.add_field(name='Status', value=f"{escrow_obj.status}")
            else:                
                embed = discord.Embed(title="Error!!", description=f"You cannot cancel the escrow of status {escrow_obj.status}.")
        else:
            embed = discord.Embed(title="Error!!", description="404 Not Found.")
    else:
        embed = discord.Embed(title="Error!!", description="You donot have permission to perform this action.")

    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="agent",
             name="release",
             description="Cancel escrow!!",
             options=[
                 create_option(
                     name="escrow_id",
                     description="Enter escrow id you want to cancel!",
                     option_type=3,
                     required=True
                 ),
                 create_option(
                     name="user",
                     description="Enter user to release the funds to.",
                     option_type=6,
                     required=True
                 )
             ]
             )
async def agent_release(ctx, escrow_id: str, user):

    if int(settings.AGENT_ROLE_ID) in [y.id for y in ctx.author.roles]:

        if Escrow.objects.filter(Q(uuid_hex=escrow_id),
                                 Q(status=Escrow.DISPUTE),
                                 Q(initiator__discord_id=user.id) | Q(successor__discord_id=user.id)).exists():

            escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)
            escrow_obj.status = Escrow.ADMIN_SETTLED

            if user.id == escrow_obj.initiator.discord_id:
                escrow_obj.initiator.locked -= escrow_obj.amount
                escrow_obj.settled_towards = Escrow.INITIATOR
                escrow_obj.initiator.save()
                escrow_obj.save()
            else:
                escrow_obj.initiator.locked -= escrow_obj.amount
                escrow_obj.initiator.balance -= escrow_obj.amount
                escrow_obj.successor.balance += int(escrow_obj.amount * (100 - settings.CROW_BOT_FEE) / 100)
                escrow_obj.initiator.save()
                escrow_obj.successor.save()
                escrow_obj.save()

            embed = discord.Embed(title="Success!!", description="")
            embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
            embed.add_field(name='Amount', value=f"{escrow_obj.amount}")
            embed.add_field(name='Status', value=f"{escrow_obj.status}")

        else:
            embed = discord.Embed(title="Error!!", description="Disputed escrow Not found or the user does not exist for the escrow.")
    else:
        embed = discord.Embed(title="Error!!", description="You donot have permission to perform this action.")

    await ctx.send(embed=embed, hidden=True)


@slash.slash(name="kill", description="Kill the bot!!")
async def kill(ctx):
    if int(ctx.author.id) == int(settings.MANAGER_ID):
        print("Shutting Down the bot")
        await ctx.send("Bot Shut Down", hidden=True)
        await client.close()
    else:
        await ctx.send("#DonotKillCrowBot", hidden=True)

client.run(TOKEN)
