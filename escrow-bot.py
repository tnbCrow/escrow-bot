import os
import django
from discord_slash.context import ComponentContext
from discord.ext import commands
import discord
from discord_slash import SlashCommand
from discord_slash.utils.manage_components import create_button, create_actionrow
from discord_slash.model import ButtonStyle


# Django Setup on bot
DJANGO_DIRECTORY = os.getcwd()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.environ["DJANGO_SETTINGS_MODULE"])
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

from django.conf import settings
from django.db.models import Q, F
from asgiref.sync import sync_to_async

from core.utils.scan_chain import match_transaction, check_confirmation, scan_chain
from core.utils.shortcuts import convert_to_int, get_or_create_tnbc_wallet, get_or_create_discord_user, convert_to_decimal
from core.models.wallets import ThenewbostonWallet
from core.models.statistics import Statistic
from escrow.utils import get_or_create_user_profile, post_trade_to_api, create_offer_table
from escrow.models.escrow import Escrow
from escrow.models.advertisement import Advertisement

# Environment Variables
TOKEN = os.environ['CROW_DISCORD_TOKEN']

# Initialize the Slash commands
bot = commands.Bot(command_prefix=">")
slash = SlashCommand(bot, sync_commands=True)


@bot.event
async def on_ready():
    print("------------------------------------")
    print("tnbCrow Bot Running:")
    print("------------------------------------")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="/help"))

for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')


@slash.subcommand(base="help", name="general", description="List of Commands from General Category")
async def help_general(ctx):
    await ctx.defer(hidden=True)
    embed = discord.Embed(title="General Commands", color=0xe81111)
    embed.add_field(name="/balance", value="Check your crow bot balance.", inline=False)
    embed.add_field(name="/deposit tnbc", value="Deposit TNBC into your crow bot account.", inline=False)
    embed.add_field(name="/withdraw tnbc amount: AMOUNT", value="Withdraw TNBC into your TNBC wallet.", inline=False)
    embed.add_field(name="/set_withdrawl_address tnbc address: ADDRESS", value="Set a new TNBC withdrawal address.", inline=False)
    embed.add_field(name="/transactions tnbc", value="Check TNBC transaction history.", inline=False)
    embed.add_field(name="/profile user: USER", value="Check user's crow bot profile.", inline=False)
    embed.add_field(name="/payment_method add", value="Add a new payment method.", inline=False)
    embed.add_field(name="/payment_method all", value="List all your payment methods.", inline=False)
    embed.add_field(name="/payment_method remove", value="Delete particular payment method.", inline=False)
    embed.add_field(name="/rate", value="Check the last OTC trade rate of TNBC.")
    embed.add_field(name="/stats", value="Check TNBC price statistics.")
    embed.add_field(name="/guide buyer", value="Buyer guide for using crow bot.")
    embed.add_field(name="/guide seller", value="Seller guide for using crow bot.")
    embed.set_thumbnail(url=bot.user.avatar_url)
    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="help", name="advertisement", description="List of Commands related to advertisements.")
async def help_advertisement(ctx):
    await ctx.defer(hidden=True)
    embed = discord.Embed(title="Advertisement Related Commands", color=0xe81111)
    embed.add_field(name="/adv create amount: AMOUNT price: PRICE", value="Create a new advertisement.", inline=False)
    embed.add_field(name="/adv all", value="List all active advertisements.", inline=False)
    embed.add_field(name="/adv my", value="List all your active advertisements.", inline=False)
    embed.add_field(name="/adv cancel advertisement_id: ID", value="Cancel an active advertisement.", inline=False)
    embed.add_field(name="/adv status advertisement_id: ID", value="Check the status of the particular advertisement.", inline=False)
    embed.add_field(name="/adv buy advertisement_id: ID amount_of_tnbc: AMOUNT", value="Buy TNBC from the advertisement.", inline=False)
    embed.set_thumbnail(url=bot.user.avatar_url)
    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="help", name="escrow", description="List of Commands related to escrows.")
async def help_escrow(ctx):
    embed = discord.Embed(title="Escrow Related Commands", color=0xe81111)
    embed.add_field(name="/escrow status escrow_id: ESCROW_ID", value="Check the status of a particular escrow.")
    embed.add_field(name="/escrow all", value="List all of your ongoing escrows.", inline=False)
    embed.add_field(name="/escrow release escrow_id: ESCROW_ID", value="Release TNBC to the buyer's account.", inline=False)
    embed.add_field(name="/escrow cancel escrow_id: ESCROW_ID", value="Cancel the particular escrow. Both buyer and seller needs to use the command for escrow cancellation.")
    embed.add_field(name="/escrow dispute escrow_id: ESCROW_ID", value="In the case of disagreement while trading, raise dispute and take the case to tnbcrow agent.", inline=False)
    embed.add_field(name="/escrow history escrow_id: ESCROW_ID", value="List all of your completed escrows.", inline=False)
    embed.set_thumbnail(url=bot.user.avatar_url)
    await ctx.send(embed=embed, hidden=True)


@bot.event
async def on_message(message):
    # ignore bot's own message
    if message.author.id == bot.user.id:
        return

    # Delete old messages by the user in #trade channel
    if message.channel.id == int(settings.TRADE_CHANNEL_ID):
        async for oldMessage in message.channel.history():
            if oldMessage.author == message.author and oldMessage.id != message.id:
                await oldMessage.delete()


@bot.event
async def on_component(ctx: ComponentContext):

    button = ctx.custom_id.split('_')

    button_type = button[0]

    if button_type == "chainscan":

        await ctx.defer(hidden=True)

        scan_chain()

        if os.environ['CHECK_TNBC_CONFIRMATION'] == 'True':

            check_confirmation()

        match_transaction()

        discord_user = get_or_create_discord_user(ctx.author.id)
        tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

        embed = discord.Embed(title="Scan Completed", color=0xe81111)
        embed.add_field(name='New Balance', value=convert_to_int(tnbc_wallet.balance))
        embed.add_field(name='Locked Amount', value=convert_to_int(tnbc_wallet.locked))
        embed.add_field(name='Available Balance', value=convert_to_int(tnbc_wallet.get_available_balance()))
        embed.set_footer(text="Use /transactions tnbc command check your transaction history.")

        await ctx.send(embed=embed, hidden=True, components=[create_actionrow(create_button(custom_id="chainscan", style=ButtonStyle.green, label="Check Again"))])

    elif button_type == "escrowcancelforbid":

        await ctx.defer(hidden=True)
        message = "If you've already sent the payment to the seller, please ask them to release the escrow.\n\nIn the case of disputes, please use the command `/admin dispute escrow_id: ID` to raise dispute and an agent will help to resolve the dispute."
        await ctx.send(message, hidden=True)

    elif button_type == "escrowcancel":

        await ctx.defer(hidden=True)

        escrow_id = button[1]

        discord_user = get_or_create_discord_user(ctx.author.id)

        if Escrow.objects.filter(Q(initiator=discord_user) |
                                 Q(successor=discord_user),
                                 Q(uuid_hex=escrow_id)).exists():

            escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

            if escrow_obj.status == Escrow.OPEN:

                if int(escrow_obj.successor.discord_id) == ctx.author.id:

                    escrow_obj.status = Escrow.CANCELLED
                    escrow_obj.save()

                    embed = discord.Embed(title="Escrow Cancelled Successfully", description="", color=0xe81111)
                    embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
                    embed.add_field(name='Amount', value=f"{convert_to_int(escrow_obj.amount)} TNBC")
                    embed.add_field(name='Fee', value=f"{convert_to_int(escrow_obj.fee)} TNBC")
                    embed.add_field(name='Price (USDT)', value=convert_to_decimal(escrow_obj.price))
                    embed.add_field(name='Status', value=f"{escrow_obj.status}")

                    conversation_channel = bot.get_channel(int(escrow_obj.conversation_channel_id))
                    if conversation_channel:
                        await conversation_channel.send(embed=embed)

                    sell_advertisement, created = Advertisement.objects.get_or_create(owner=escrow_obj.initiator, price=escrow_obj.price, defaults={'amount': 0})
                    sell_advertisement.amount += escrow_obj.amount
                    sell_advertisement.status = Advertisement.OPEN
                    sell_advertisement.save()

                    offer_channel = bot.get_channel(int(settings.OFFER_CHANNEL_ID))
                    offer_table = create_offer_table(20)

                    async for oldMessage in offer_channel.history():
                        await oldMessage.delete()

                    await offer_channel.send(f"**Sell Advertisements - Escrow Protected.**\nUse `/guide buyer` command for the buyer's guide and `/guide seller` for seller's guide to trade on tnbCrow discord server.\n```{offer_table}```")
                    await ctx.send(embed=embed, hidden=True)
                else:
                    embed = discord.Embed(title="Error!", description="Only the buyer can cancel the escrow. Use the command /escrow dispute if they're not responding.", color=0xe81111)
                    await ctx.send(embed=embed, hidden=True)
            else:
                embed = discord.Embed(title="Error!", description=f"You cannot cancel the escrow of status {escrow_obj.status}.", color=0xe81111)
                await ctx.send(embed=embed, hidden=True)
        else:
            embed = discord.Embed(title="Error!", description="404 Not Found.", color=0xe81111)
            await ctx.send(embed=embed, hidden=True)

    elif button_type == "escrowreleaseforbid":

        await ctx.defer(hidden=True)
        message = "Ask the buyer to send the payment before releasing the escrow.\n\nIn the case of disputes, please use the command `/admin dispute escrow_id: ID` to raise dispute and an agent will help to resolve the dispute."
        await ctx.send(message, hidden=True)

    elif button_type == "escrowrelease":

        await ctx.defer(hidden=True)

        escrow_id = button[1]
        discord_user = get_or_create_discord_user(ctx.author.id)

        if Escrow.objects.filter(uuid_hex=escrow_id, initiator=discord_user).exists():

            escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

            if escrow_obj.status == Escrow.OPEN:

                escrow_obj.status = Escrow.COMPLETED
                escrow_obj.save()

                seller_wallet = get_or_create_tnbc_wallet(discord_user)
                seller_wallet.balance -= escrow_obj.amount
                seller_wallet.locked -= escrow_obj.amount
                seller_wallet.save()

                buyer_wallet = get_or_create_tnbc_wallet(escrow_obj.successor)
                buyer_wallet.balance += escrow_obj.amount - escrow_obj.fee
                buyer_wallet.save()

                statistic, created = Statistic.objects.get_or_create(title="main")
                statistic.total_fees_collected += escrow_obj.fee
                statistic.save()

                buyer_profile = get_or_create_user_profile(escrow_obj.successor)
                buyer_profile.total_escrows += 1
                buyer_profile.total_tnbc_escrowed += escrow_obj.amount - escrow_obj.fee
                buyer_profile.save()

                seller_profile = get_or_create_user_profile(discord_user)
                seller_profile.total_escrows += 1
                seller_profile.total_tnbc_escrowed += escrow_obj.amount
                seller_profile.save()

                embed = discord.Embed(title="Escrow Released Successfully", description="", color=0xe81111)
                embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
                embed.add_field(name='Amount', value=f"{convert_to_int(escrow_obj.amount)} TNBC")
                embed.add_field(name='Fee', value=f"{convert_to_int(escrow_obj.fee)} TNBC")
                embed.add_field(name='Buyer Received', value=f"{convert_to_int(escrow_obj.amount - escrow_obj.fee)} TNBC")
                embed.add_field(name='Price (USDT)', value=convert_to_decimal(escrow_obj.price))
                embed.add_field(name='Status', value=f"{escrow_obj.status}")

                conversation_channel = bot.get_channel(int(escrow_obj.conversation_channel_id))
                if conversation_channel:
                    await conversation_channel.send(embed=embed)

                recent_trade_channel = bot.get_channel(int(settings.RECENT_TRADE_CHANNEL_ID))

                await recent_trade_channel.send(f"Recent Trade: {convert_to_int(escrow_obj.amount)} TNBC at ${convert_to_decimal(escrow_obj.price)} each")

                post_trade_to_api(convert_to_int(escrow_obj.amount), escrow_obj.price)
                await ctx.send(embed=embed, hidden=True)

            else:
                embed = discord.Embed(title="Error!", description=f"You cannot release the escrow of status {escrow_obj.status}.", color=0xe81111)
                await ctx.send(embed=embed, hidden=True)
        else:
            embed = discord.Embed(title="Error!", description="You do not have permission to perform the action.", color=0xe81111)
            await ctx.send(embed=embed, hidden=True)
    else:
        await ctx.send("Where did you find this button??", hidden=True)


@slash.slash(name="kill", description="Kill the bot!")
async def kill(ctx):

    await ctx.defer(hidden=True)

    if int(ctx.author.id) == int(settings.BOT_MANAGER_ID):
        print("Shutting Down the bot")
        await ctx.send("Bot Shut Down", hidden=True)
        await bot.close()
    else:
        embed = discord.Embed(title="Nope", description="", color=0xe81111)
        embed.set_image(url="https://i.ibb.co/zQc3xDp/download-min-1.png")
        await ctx.send(embed=embed, hidden=True)

bot.run(TOKEN)
