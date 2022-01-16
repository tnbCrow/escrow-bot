import discord
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option
from core.utils.shortcuts import convert_to_int, get_or_create_tnbc_wallet, get_or_create_discord_user, check_withdrawal_address_valid, comma_seperate_amount
from discord_slash.utils.manage_components import create_button, create_actionrow
from django.conf import settings
from discord_slash.model import ButtonStyle
from asgiref.sync import sync_to_async
import humanize

from core.utils.send_tnbc import estimate_fee, withdraw_tnbc
from core.models.transactions import Transaction
from core.models.statistics import Statistic
from core.models.users import UserTransactionHistory
from core.utils.shortcuts import get_wallet_balance
from escrow.models.advertisement import Advertisement

from escrow.models.payment_method import PaymentMethod
from escrow.utils import get_or_create_user_profile, create_offer_table


class user(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_subcommand(base="deposit", name="tnbc", description="Deposit TNBC into your crow account.")
    async def user_deposit(self, ctx):

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

    @cog_ext.cog_slash(name="balance", description="Check User Balance.")
    async def user_balance(self, ctx):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)
        tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

        embed = discord.Embed(color=0xe81111)
        embed.add_field(name='Balance (TNBC)', value=comma_seperate_amount(convert_to_int(tnbc_wallet.balance)))
        embed.add_field(name='Locked (TNBC)', value=comma_seperate_amount(convert_to_int(tnbc_wallet.locked)))
        embed.add_field(name='Available (TNBC)', value=comma_seperate_amount(convert_to_int(tnbc_wallet.get_available_balance())), inline=False)
        embed.set_footer(text="Use /transactions tnbc command check your transaction history.")

        await ctx.send(embed=embed, hidden=True, components=[create_actionrow(create_button(custom_id="deposittnbc", style=ButtonStyle.green, label="👛Deposit"))])

    @cog_ext.cog_subcommand(base="withdraw",
                            name="tnbc",
                            description="Withdraw TNBC into your external wallet.",
                            options=[
                                create_option(
                                    name="tnbc_address",
                                    description="TNBC address to send TNBC to.",
                                    option_type=3,
                                    required=True
                                ),
                                create_option(
                                    name="amount",
                                    description="No of TNBC to withdraw.",
                                    option_type=4,
                                    required=True
                                )
                            ]
                            )
    async def user_withdraw(self, ctx, tnbc_address: str, amount: int):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)
        tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

        response, fee = estimate_fee()

        if check_withdrawal_address_valid(tnbc_address):
            if response:
                if not amount < 1:
                    if convert_to_int(tnbc_wallet.get_available_balance()) < amount + fee:
                        embed = discord.Embed(title="Inadequate Funds!",
                                              description=f"You only have {convert_to_int(tnbc_wallet.get_available_balance()) - fee} withdrawable TNBC (network fees included) available. \n Use `/deposit tnbc` to deposit TNBC.",
                                              color=0xe81111)

                    else:
                        hot_wallet_balance = get_wallet_balance(settings.TNBCROW_BOT_ACCOUNT_NUMBER)

                        if hot_wallet_balance >= amount + fee:

                            block_response, fee = withdraw_tnbc(tnbc_address, amount, tnbc_wallet.memo)

                            if block_response:
                                if block_response.status_code == 201:
                                    txs = Transaction.objects.create(confirmation_status=Transaction.WAITING_CONFIRMATION,
                                                                     transaction_status=Transaction.IDENTIFIED,
                                                                     direction=Transaction.OUTGOING,
                                                                     account_number=tnbc_address,
                                                                     amount=amount * settings.TNBC_MULTIPLICATION_FACTOR,
                                                                     fee=fee * settings.TNBC_MULTIPLICATION_FACTOR,
                                                                     signature=block_response.json()['signature'],
                                                                     block=block_response.json()['id'],
                                                                     memo=tnbc_wallet.memo)
                                    converted_amount_plus_fee = (amount + fee) * settings.TNBC_MULTIPLICATION_FACTOR

                                    tnbc_wallet.balance -= converted_amount_plus_fee
                                    tnbc_wallet.save()

                                    UserTransactionHistory.objects.create(user=discord_user, amount=converted_amount_plus_fee, type=UserTransactionHistory.WITHDRAW, transaction=txs)

                                    statistic, created = Statistic.objects.get_or_create(title="main")
                                    statistic.total_balance -= converted_amount_plus_fee
                                    statistic.save()

                                    embed = discord.Embed(title="Coins Withdrawn.",
                                                          description=f"Successfully withdrawn {amount} TNBC to {tnbc_address} \n Use `/balance` to check your new balance.",
                                                          color=0xe81111)
                                else:
                                    embed = discord.Embed(title="Error!", description="Please try again later.", color=0xe81111)
                            else:
                                embed = discord.Embed(title="Error!", description="Can not send transaction block to the bank, Try Again.", color=0xe81111)
                        else:
                            embed = discord.Embed(title="Error!", description="Not enough TNBC available in the hot wallet, contact @admin.", color=0xe81111)
                else:
                    embed = discord.Embed(title="Error!", description="You cannot withdraw less than 1 TNBC.", color=0xe81111)
            else:
                embed = discord.Embed(title="Error!", description="Could not load fee info from the bank.", color=0xe81111)
        else:
            embed = discord.Embed(title="Error!", description="Invalid TNBC withdrawal address.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="transactions", name="tnbc", description="Check Transaction History.")
    async def user_transactions(self, ctx):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)

        transactions = (await sync_to_async(UserTransactionHistory.objects.filter)(user=discord_user)).order_by('-created_at')[:8]

        embed = discord.Embed(title="Transaction History", description="", color=0xe81111)

        for txs in transactions:

            natural_day = humanize.naturalday(txs.created_at)

            embed.add_field(name='\u200b', value=f"{txs.type} - {convert_to_int(txs.amount)} TNBC - {natural_day}", inline=False)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_slash(name="profile",
                       description="Check User Profile.",
                       options=[
                           create_option(
                               name="user",
                               description="User you want to check the profile of.",
                               option_type=6,
                               required=True
                           )
                       ])
    async def user_profile(self, ctx, user: discord.Member):

        await ctx.defer()

        discord_user = get_or_create_discord_user(user.id)
        user_profile = get_or_create_user_profile(discord_user)

        embed = discord.Embed(title=f"{user.name}'s Crow Bot Profile", description="", color=0xe81111)
        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name='Total Trade(s)', value=user_profile.total_escrows)
        embed.add_field(name='Total Dispute(s)', value=user_profile.total_disputes)

        await ctx.send(embed=embed)

    @cog_ext.cog_subcommand(base="payment_method",
                            name="add",
                            description="Add a new payment method.",
                            options=[
                                create_option(
                                    name="name_of_payment_method",
                                    description="Eg: Bitcoin, Paypal, Bank Of America.",
                                    option_type=3,
                                    required=True
                                ),
                                create_option(
                                    name="details",
                                    description="Eg: BITCOIN ADDRESS, PAYPAL_EMAIL, BANK_ACCOUNT_DETAILS.",
                                    option_type=3,
                                    required=True
                                ),
                                create_option(
                                    name="conditions",
                                    description="Additional conditions for trade. Eg: Dont send less than 0.01 BTC, send as friend on paypal.",
                                    option_type=3,
                                    required=True
                                )
                            ]
                            )
    async def payment_method_add(self, ctx, name_of_payment_method: str, details: str, conditions: str):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)

        embed = discord.Embed(color=0xe81111)

        if PaymentMethod.objects.filter(user=discord_user).count() <= 5:

            PaymentMethod.objects.create(user=discord_user, name=name_of_payment_method, detail=details, condition=conditions)

            embed.add_field(name="Success", value="Payment method added successfully.", inline=False)
            embed.add_field(name="Payment Method", value=name_of_payment_method, inline=False)
            embed.add_field(name="Details", value=details, inline=False)
            embed.add_field(name="Conditions", value=conditions, inline=False)
            embed.set_footer(text="Use /payment_method all command to list all your active payment methods.")

            if Advertisement.objects.filter(owner=discord_user, side=Advertisement.BUY).exists():

                buy_offer_channel = self.bot.get_channel(int(settings.TRADE_CHANNEL_ID))
                offer_table = create_offer_table(Advertisement.BUY, 20)

                async for oldMessage in buy_offer_channel.history():
                    await oldMessage.delete()
                await buy_offer_channel.send(f"**Buy Advertisements.**```{offer_table}```\nUse the command `/adv sell advertisement_id: ID amount_of_tnbc: AMOUNT` to sell tnbc to above advertisement.\nOr `/adv create` command to create your own buy/ sell advertisements.")

            if Advertisement.objects.filter(owner=discord_user, side=Advertisement.SELL).exists():

                sell_order_channel = self.bot.get_channel(int(settings.OFFER_CHANNEL_ID))
                offer_table = create_offer_table(Advertisement.SELL, 20)

                async for oldMessage in sell_order_channel.history():
                    await oldMessage.delete()

                await sell_order_channel.send(f"**Sell Advertisements - Escrow Protected.**\n```{offer_table}```\nUse the command `/adv buy advertisement_id: ID amount: AMOUNT` to buy TNBC from the above advertisements.\nOr `/adv create` to create your own buy/ sell advertisement.")

        else:
            embed.add_field(name="Error", value="You cannot add more than five payment methods. Try /payment_method remove command to remove payment methods.")

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="payment_method", name="all", description="List all your active payment methods.")
    async def payment_method_all(self, ctx):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)

        if PaymentMethod.objects.filter(user=discord_user).exists():
            payment_methods = await sync_to_async(PaymentMethod.objects.filter)(user=discord_user)

            embed = discord.Embed(color=0xe81111)

            for payment_method in payment_methods:
                embed.add_field(name='ID', value=f"{payment_method.uuid_hex}", inline=False)
                embed.add_field(name='Payment Method', value=payment_method.name)
                embed.add_field(name='Details', value=payment_method.detail)
                embed.add_field(name='Conditions', value=payment_method.condition)
                embed.set_footer(text="Use /payment_method remove command to delete the payment methods.")

        else:
            embed = discord.Embed(title="Oops..",
                                  description="No payment methods found. Use /payment_method add command to add your new payment method.",
                                  color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="payment_method",
                            name="remove",
                            description="Remove a particular payment method.",
                            options=[
                                create_option(
                                    name="payment_method_id",
                                    description="ID of the payment method.",
                                    option_type=3,
                                    required=True
                                )
                            ]
                            )
    async def payment_method_remove(self, ctx, payment_method_id: str):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)

        if PaymentMethod.objects.filter(user=discord_user, uuid_hex=payment_method_id).exists():
            PaymentMethod.objects.filter(user=discord_user, uuid_hex=payment_method_id).delete()
            embed = discord.Embed(title="Success", description="Payment method deleted successfully.", color=0xe81111)

            if Advertisement.objects.filter(owner=discord_user, side=Advertisement.BUY).exists():

                buy_offer_channel = self.bot.get_channel(int(settings.TRADE_CHANNEL_ID))
                offer_table = create_offer_table(Advertisement.BUY, 20)

                async for oldMessage in buy_offer_channel.history():
                    await oldMessage.delete()
                await buy_offer_channel.send(f"**Buy Advertisements.**```{offer_table}```\nUse the command `/adv sell advertisement_id: ID amount_of_tnbc: AMOUNT` to sell tnbc to above advertisement.\nOr `/adv create` command to create your own buy/ sell advertisements.")

            if Advertisement.objects.filter(owner=discord_user, side=Advertisement.SELL).exists():

                sell_order_channel = self.bot.get_channel(int(settings.OFFER_CHANNEL_ID))
                offer_table = create_offer_table(Advertisement.SELL, 20)

                async for oldMessage in sell_order_channel.history():
                    await oldMessage.delete()
                await sell_order_channel.send(f"**Sell Advertisements - Escrow Protected.**\n```{offer_table}```\nUse the command `/adv buy advertisement_id: ID amount: AMOUNT` to buy TNBC from the above advertisements.\nOr `/adv create` to create your own buy/ sell advertisement.")

        else:
            embed = discord.Embed(title="Error!", description="404 Not Found.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="guide",
                            name="seller",
                            description="Guide for sellers to trade on tnbcrow discord server.")
    async def guide_seller(self, ctx):

        await ctx.defer(hidden=True)

        embed = discord.Embed(title="Seller Guide | Crow Bot", description="", color=0xe81111)
        embed.add_field(name="Creating Sell Advertisement", value="------------------------------", inline=False)
        embed.add_field(name="1. Deposit TNBC", value="Use the command `/deposit tnbc` to deposit tnbc into your crow bot account.", inline=False)
        embed.add_field(name="2. Set your desired payment method", value="Use the command `/payment_method add` command to add payment method you'd like to receive the payment.", inline=False)
        embed.add_field(name="3. Create an advertisement", value="Create an advertisement using `/adv create` command.", inline=False)
        embed.add_field(name="4. Wait for the buyer", value="Once buyer buys from the advertisement, private channel is created within this server.", inline=False)
        embed.add_field(name="5. Discuss the payment details", value="Discuss the payment details in the private channel and wait for buyer to send the payment.", inline=False)
        embed.add_field(name="6. Release the escrow", value="Once you've received payment, use the command `/escrow release` to release TNBC into buyer's account.", inline=False)
        embed.add_field(name="Selling to buy advertisements", value="------------------------", inline=False)
        embed.add_field(name="1. Check the buy offers", value="Navigate to #buy-offers to check all buy offers.", inline=False)
        embed.add_field(name="2. Sell to the offer", value="Use the command `/adv sell advertisement_id: ID amount_of_tnbc: AMOUNT` to sell tnbc to the buy advertisement.", inline=False)
        embed.add_field(name="3. Discuss the payment details", value="Discuss the payment details in the private channel that was created and wait for the buyer to send the payment.", inline=False)
        embed.add_field(name="4. Release the escrow", value="Once you've received payment, use the command `/escrow release` to release TNBC into buyer's account.", inline=False)
        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="guide",
                            name="buyer",
                            description="Guide for buyers to trade on tnbcrow discord server.")
    async def guide_buyer(self, ctx):

        await ctx.defer(hidden=True)
        embed = discord.Embed(title="Buyer Guide | Crow Bot", description="", color=0xe81111)
        embed.add_field(name="Buying from sell advertisements", value="------------------------", inline=False)
        embed.add_field(name="1. Check the available sell advertisements", value="Navigate to #sell-orders and check all available sell orders.", inline=False)
        embed.add_field(name="2. Buy from the advertisement", value="Use the command `/adv buy` to buy tnbc from the advertisement. Private channel is created within the discord server.", inline=False)
        embed.add_field(name="3. Discuss the payment details", value="Discuss the payment details in the private channel.", inline=False)
        embed.add_field(name="4. Send the payment", value="Send agreed payment amount using the method.", inline=False)
        embed.add_field(name="5. Wait for the seller to release escrow", value="Once the payment is received, the seller will release escrow. You'll be notified in private channel about the status of the escrow.", inline=False)
        embed.add_field(name="By creating buy advertisements", value="------------------------", inline=False)
        embed.add_field(name="1. Create buy advertisement", value="Use the command `/adv create side: Buying amount: AMOUNT price: PRICE`.", inline=False)
        embed.add_field(name="2. Wait for seller", value="Once the seller sells tnbc to the buy advertisement, a private channel is created within tnbcrow discord server.", inline=False)
        embed.add_field(name="3. Discuss the payment details", value="Discuss the payment details in the private channel.", inline=False)
        embed.add_field(name="4. Send the payment", value="Send agreed payment amount using the method.", inline=False)
        embed.add_field(name="5. Wait for the seller to release escrow", value="Once the payment is received, the seller will release escrow. You'll be notified in private channel about the status of the escrow.", inline=False)
        await ctx.send(embed=embed, hidden=True)


def setup(bot):
    bot.add_cog(user(bot))
