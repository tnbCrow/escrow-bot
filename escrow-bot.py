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
from django.db.models import Q
from asgiref.sync import sync_to_async

from core.utils.scan_chain import match_transaction, check_confirmation, scan_chain
from core.utils.shortcuts import convert_to_int, get_or_create_tnbc_wallet, get_or_create_discord_user, convert_to_decimal, comma_seperated_int
from core.models.statistics import Statistic
from core.utils.logger import log_send

from escrow.utils import get_or_create_user_profile, post_trade_to_api, create_offer_table
from escrow.models.escrow import Escrow
from escrow.models.advertisement import Advertisement
from escrow.models.escrow_review import EscrowReview

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
    embed.add_field(name="/withdraw tnbc tnbc_address: ADDRESS amount: AMOUNT", value="Withdraw TNBC into your TNBC wallet.", inline=False)
    embed.add_field(name="/transactions tnbc", value="Check TNBC transaction history.", inline=False)
    embed.add_field(name="/payment_method add", value="Add a new payment method.", inline=False)
    embed.add_field(name="/payment_method all", value="List all your payment methods.", inline=False)
    embed.add_field(name="/payment_method remove", value="Delete particular payment method.", inline=False)
    embed.add_field(name="/guide buyer", value="Buyer's guide for using crow bot.")
    embed.add_field(name="/guide seller", value="Seller's guide for using crow bot.")
    embed.set_thumbnail(url=bot.user.avatar_url)
    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="help", name="advertisement", description="List of Commands related to advertisements.")
async def help_advertisement(ctx):
    await ctx.defer(hidden=True)
    embed = discord.Embed(title="Advertisement Related Commands", color=0xe81111)
    embed.add_field(name="/adv create amount: AMOUNT price: PRICE", value="Create a new advertisement.", inline=False)
    embed.add_field(name="/adv my", value="List all your active advertisements.", inline=False)
    embed.add_field(name="/adv cancel advertisement_id: ID", value="Cancel an active advertisement.", inline=False)
    embed.add_field(name="/adv buy advertisement_id: ID amount_of_tnbc: AMOUNT", value="Buy TNBC from the advertisement.", inline=False)
    embed.add_field(name="/adv sell advertisement_id: ID amount_of_tnbc: AMOUNT", value="Sell TNBC to the advertisement.", inline=False)
    embed.set_thumbnail(url=bot.user.avatar_url)
    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="help", name="escrow", description="List of Commands related to escrows.")
async def help_escrow(ctx):
    embed = discord.Embed(title="Escrow Related Commands", color=0xe81111)
    embed.add_field(name="/escrow all", value="List all of your ongoing escrows.", inline=False)
    embed.add_field(name="/escrow release escrow_id: ESCROW_ID", value="Release TNBC to the buyer's account.", inline=False)
    embed.add_field(name="/escrow cancel escrow_id: ESCROW_ID", value="Cancel the particular escrow. Both buyer and seller needs to use the command for escrow cancellation.")
    embed.add_field(name="/escrow dispute escrow_id: ESCROW_ID", value="In the case of disagreement while trading, raise dispute and take the case to tnbcrow agent.", inline=False)
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
        embed.add_field(name='New Balance', value=comma_seperated_int(tnbc_wallet.balance))
        embed.add_field(name='Locked Amount', value=comma_seperated_int(tnbc_wallet.locked))
        embed.add_field(name='Available Balance', value=comma_seperated_int(tnbc_wallet.get_available_balance()))
        embed.add_field(name='Deposit did not come through?', value="Leave a message on #help")
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

                    if escrow_obj.side == Escrow.BUY:
                        buy_advertisement, created = Advertisement.objects.get_or_create(owner=escrow_obj.successor, price=escrow_obj.price, side=Advertisement.BUY, defaults={'amount': 0})
                        buy_advertisement.amount += escrow_obj.amount
                        buy_advertisement.status = Advertisement.OPEN
                        buy_advertisement.save()

                        buy_offer_channel = bot.get_channel(int(settings.TRADE_CHANNEL_ID))
                        offers = create_offer_table(Advertisement.BUY, 16)

                        seller_wallet = get_or_create_tnbc_wallet(escrow_obj.initiator)
                        seller_wallet.locked -= escrow_obj.amount + escrow_obj.fee
                        seller_wallet.save()

                        async for oldMessage in buy_offer_channel.history():
                            await oldMessage.delete()

                        await buy_offer_channel.send("**Buy Advertisements**")
                        for offer in offers:
                            await buy_offer_channel.send(f"```{offer}```")
                        await buy_offer_channel.send("Use the command `/adv sell advertisement_id: ID amount_of_tnbc: AMOUNT` to sell tnbc to above advertisement.\nOr `/adv create` command to create your own buy/ sell advertisements.")

                        await log_send(bot=bot, message=f"{ctx.author.mention} just cancelled the escrow.Escrow ID: {escrow_obj.uuid_hex}.\nBuy Adv Id: {buy_advertisement.uuid_hex}")

                    else:
                        sell_advertisement, created = Advertisement.objects.get_or_create(owner=escrow_obj.initiator, price=escrow_obj.price, side=Advertisement.SELL, defaults={'amount': 0})
                        sell_advertisement.amount += escrow_obj.amount
                        sell_advertisement.status = Advertisement.OPEN
                        sell_advertisement.save()

                        seller_wallet = get_or_create_tnbc_wallet(escrow_obj.initiator)
                        seller_wallet.locked -= escrow_obj.amount
                        seller_wallet.save()

                        sell_order_channel = bot.get_channel(int(settings.OFFER_CHANNEL_ID))
                        offers = create_offer_table(Advertisement.SELL, 16)

                        async for oldMessage in sell_order_channel.history():
                            await oldMessage.delete()

                        await sell_order_channel.send("**Sell Advertisements**")
                        for offer in offers:
                            await sell_order_channel.send(f"```{offer}```")
                        await sell_order_channel.send("Use the command `/adv buy advertisement_id: ID amount: AMOUNT` to buy TNBC from the above advertisements.\nOr `/adv create` to create your own buy/ sell advertisement.")

                        await log_send(bot=bot, message=f"{ctx.author.mention} just cancelled the escrow. Escrow ID: {escrow_obj.uuid_hex}. Sell Adv Id: {sell_advertisement.uuid_hex}")

                    embed = discord.Embed(title="Escrow Cancelled Successfully", description="", color=0xe81111)
                    embed.add_field(name='Escrow ID', value=f"{escrow_obj.uuid_hex}", inline=False)
                    embed.add_field(name='Amount', value=f"{comma_seperated_int(escrow_obj.amount)} TNBC")
                    embed.add_field(name='Fee', value=f"{comma_seperated_int(escrow_obj.fee)} TNBC")
                    embed.add_field(name='Price (USDT)', value=convert_to_decimal(escrow_obj.price))
                    embed.add_field(name='Status', value=f"{escrow_obj.status}")

                    conversation_channel = bot.get_channel(int(escrow_obj.conversation_channel_id))
                    if conversation_channel:
                        await conversation_channel.send(embed=embed)

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

                embed = discord.Embed(title="Escrow Released Successfully", description="", color=0xe81111)
                embed.add_field(name='Escrow ID', value=f"{escrow_obj.uuid_hex}", inline=False)
                embed.add_field(name='Amount', value=f"{comma_seperated_int(escrow_obj.amount)} TNBC")

                if escrow_obj.side == Escrow.BUY:
                    seller_wallet = get_or_create_tnbc_wallet(discord_user)
                    seller_wallet.balance -= escrow_obj.amount + escrow_obj.fee
                    seller_wallet.locked -= escrow_obj.amount + escrow_obj.fee
                    seller_wallet.save()

                    buyer_wallet = get_or_create_tnbc_wallet(escrow_obj.successor)
                    buyer_wallet.balance += escrow_obj.amount
                    buyer_wallet.save()

                    buyer_profile = get_or_create_user_profile(escrow_obj.successor)
                    buyer_profile.total_escrows += 1
                    buyer_profile.total_tnbc_escrowed += escrow_obj.amount
                    buyer_profile.save()

                    seller_profile = get_or_create_user_profile(discord_user)
                    seller_profile.total_escrows += 1
                    seller_profile.total_tnbc_escrowed += escrow_obj.amount + escrow_obj.fee
                    seller_profile.save()

                    embed.add_field(name='Seller Paid', value=f"{comma_seperated_int(escrow_obj.amount + escrow_obj.fee)} TNBC")
                    embed.add_field(name='Buyer Received', value=f"{comma_seperated_int(escrow_obj.amount)} TNBC")

                else:
                    seller_wallet = get_or_create_tnbc_wallet(discord_user)
                    seller_wallet.balance -= escrow_obj.amount
                    seller_wallet.locked -= escrow_obj.amount
                    seller_wallet.save()

                    buyer_wallet = get_or_create_tnbc_wallet(escrow_obj.successor)
                    buyer_wallet.balance += escrow_obj.amount - escrow_obj.fee
                    buyer_wallet.save()

                    buyer_profile = get_or_create_user_profile(escrow_obj.successor)
                    buyer_profile.total_escrows += 1
                    buyer_profile.total_tnbc_escrowed += escrow_obj.amount - escrow_obj.fee
                    buyer_profile.save()

                    seller_profile = get_or_create_user_profile(discord_user)
                    seller_profile.total_escrows += 1
                    seller_profile.total_tnbc_escrowed += escrow_obj.amount
                    seller_profile.save()

                    embed.add_field(name='Fee', value=f"{comma_seperated_int(escrow_obj.fee)} TNBC")
                    embed.add_field(name='Buyer Received', value=f"{comma_seperated_int(escrow_obj.amount - escrow_obj.fee)} TNBC")

                escrow_obj.status = Escrow.COMPLETED
                escrow_obj.save()

                statistic, created = Statistic.objects.get_or_create(title="main")
                statistic.total_fees_collected += escrow_obj.fee
                statistic.save()

                embed.add_field(name='Price (USDT)', value=convert_to_decimal(escrow_obj.price))
                embed.add_field(name='Status', value=f"{escrow_obj.status}")

                conversation_channel = bot.get_channel(int(escrow_obj.conversation_channel_id))
                if conversation_channel:
                    buyer = await bot.fetch_user(int(escrow_obj.successor.discord_id))
                    await conversation_channel.send(f"{buyer.mention} the escrow is released successfully. Please use `/balance` to check your new balance.\nOr, `/withdraw tnbc` to withdraw tnbc into your wallet.",
                                                    embed=embed)
                    await conversation_channel.send(f"{buyer.mention} {ctx.author.mention} How was your trade experience with the buyer/ seller?",
                                                    components=[
                                                        create_actionrow(
                                                            create_button(
                                                                custom_id=f"escrowreview_{escrow_obj.uuid_hex}_GOOD",
                                                                style=ButtonStyle.green,
                                                                label="👍"
                                                            ),
                                                            create_button(
                                                                custom_id=f"escrowreview_{escrow_obj.uuid_hex}_NEUTRAL",
                                                                style=ButtonStyle.blue,
                                                                label="😐"
                                                            ),
                                                            create_button(
                                                                custom_id=f"escrowreview_{escrow_obj.uuid_hex}_BAD",
                                                                style=ButtonStyle.red,
                                                                label="👎"
                                                            )
                                                        )
                                                    ])

                recent_trade_channel = bot.get_channel(int(settings.RECENT_TRADE_CHANNEL_ID))

                await recent_trade_channel.send(f"Recent Trade: {comma_seperated_int(escrow_obj.amount)} TNBC at {convert_to_decimal(escrow_obj.price)} USDC each.")
                await log_send(bot=bot, message=f"{ctx.author.mention} released the escrow. Escrow ID: {escrow_obj.uuid_hex}")

                post_trade_to_api(convert_to_int(escrow_obj.amount), escrow_obj.price)

                guild = bot.get_guild(int(settings.GUILD_ID))
                await guild.me.edit(nick=f"Price: {convert_to_decimal(escrow_obj.price)}")

                await ctx.send(embed=embed, hidden=True)

            else:
                embed = discord.Embed(title="Error!", description=f"You cannot release the escrow of status {escrow_obj.status}.", color=0xe81111)
                await ctx.send(embed=embed, hidden=True)
        else:
            embed = discord.Embed(title="Error!", description="You do not have permission to perform the action.", color=0xe81111)
            await ctx.send(embed=embed, hidden=True)

    elif button_type == "deposittnbc":
        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)
        tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

        qr_data = f"{{\"address\":\"{settings.TNBCROW_BOT_ACCOUNT_NUMBER}\",\"memo\":\"{tnbc_wallet.memo}\"}}"

        embed = discord.Embed(title="Send TNBC to the address with memo.", color=0xe81111)
        embed.add_field(name='Address', value=settings.TNBCROW_BOT_ACCOUNT_NUMBER, inline=False)
        embed.add_field(name='MEMO (MEMO is required, or you will lose your coins)', value=tnbc_wallet.memo, inline=False)
        embed.set_image(url=f"https://chart.googleapis.com/chart?chs=150x150&cht=qr&chl={qr_data}")
        embed.set_footer(text="Or, scan the QR code using Keysign Mobile App.")

        await ctx.send(embed=embed, hidden=True, components=[create_actionrow(create_button(custom_id="chainscan", style=ButtonStyle.green, label="Sent? Check new balance."))])

    elif button_type == "escrowreview":

        escrow_id = button[1]
        feedback_type = button[2]

        discord_user = get_or_create_discord_user(ctx.author.id)

        if Escrow.objects.filter(Q(initiator=discord_user) |
                                 Q(successor=discord_user),
                                 Q(uuid_hex=escrow_id)).exists():

            escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

            escrow_review, created = EscrowReview.objects.get_or_create(escrow=escrow_obj, feedback_by=discord_user, defaults={'feedback': feedback_type})

            if discord_user == escrow_obj.successor:
                user_profile = get_or_create_user_profile(escrow_obj.initiator)
            else:
                user_profile = get_or_create_user_profile(escrow_obj.successor)

            if created:
                user_profile.total_feedback += 1
                user_profile.save()
            else:
                if escrow_review.feedback == EscrowReview.GOOD:
                    user_profile.positive_feeback -= 1
                elif escrow_review.feedback == EscrowReview.BAD:
                    user_profile.negative_feedback -= 1
                else:
                    user_profile.neutral_feedback -= 1
                user_profile.save()

            if feedback_type == "GOOD":
                escrow_review.feedback = EscrowReview.GOOD
                user_profile.positive_feeback += 1
            elif feedback_type == "BAD":
                escrow_review.feedback = EscrowReview.BAD
                user_profile.negative_feedback += 1
            else:
                escrow_review.feedback = EscrowReview.NEUTRAL
                user_profile.neutral_feedback += 1

            escrow_review.save()
            user_profile.save()

            await ctx.send(f"{ctx.author.mention} gave a review of their experience while trading.")

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
