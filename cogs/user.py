import discord
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option
from core.utils.shortcuts import convert_to_int, get_or_create_tnbc_wallet, get_or_create_discord_user
from discord_slash.utils.manage_components import create_button, create_actionrow
from django.conf import settings
from discord_slash.model import ButtonStyle
from core.utils.send_tnbc import estimate_fee, withdraw_tnbc
from core.models.transactions import Transaction
from core.models.statistics import Statistic
from core.models.users import UserTransactionHistory
from escrow.models.payment_method import PaymentMethod
from escrow.utils import get_or_create_user_profile
from asgiref.sync import sync_to_async
import humanize


class user(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_subcommand(base="deposit", name="tnbc", description="Deposit TNBC into your crow account.")
    async def user_deposit(self, ctx):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)
        tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

        qr_data = f"{{'address':{settings.TNBCROW_BOT_ACCOUNT_NUMBER},'memo':'{tnbc_wallet.memo}'}}"

        embed = discord.Embed(title="Send TNBC to the address with memo.", color=0xe81111)
        embed.add_field(name='Warning', value="Do not deposit TNBC with Keysign Mobile Wallet/ Keysign Extension or **you'll lose your coins**.", inline=False)
        embed.add_field(name='Address', value=settings.TNBCROW_BOT_ACCOUNT_NUMBER, inline=False)
        embed.add_field(name='MEMO (MEMO is required, or you will lose your coins)', value=tnbc_wallet.memo, inline=False)
        # embed.set_image(url=f"https://chart.googleapis.com/chart?chs=150x150&cht=qr&chl={qr_data}")
        # embed.set_footer(text="Or, scan the QR code using Keysign Mobile App.")

        await ctx.send(embed=embed, hidden=True, components=[create_actionrow(create_button(custom_id="chain_scan", style=ButtonStyle.green, label="Sent? Check new balance."))])

    @cog_ext.cog_slash(name="balance", description="Check User Balance.")
    async def user_balance(self, ctx):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)
        tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

        embed = discord.Embed(color=0xe81111)
        embed.add_field(name='Withdrawal Address', value=tnbc_wallet.withdrawal_address, inline=False)
        embed.add_field(name='Balance', value=convert_to_int(tnbc_wallet.balance))
        embed.add_field(name='Locked Amount', value=convert_to_int(tnbc_wallet.locked))
        embed.add_field(name='Available Balance', value=convert_to_int(tnbc_wallet.get_available_balance()))

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="set_withdrawal_address",
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
    async def user_setwithdrawaladdress(self, ctx, address: str):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)
        tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

        if len(address) == 64:
            if address not in settings.PROHIBITED_ACCOUNT_NUMBERS:
                tnbc_wallet.withdrawal_address = address
                tnbc_wallet.save()
                embed = discord.Embed(color=0xe81111)
                embed.add_field(name='Success', value=f"Successfully set `{address}` as your withdrawal address.")
            else:
                embed = discord.Embed(color=0xe81111)
                embed.add_field(name='Error!', value="You can not set this account number as your withdrawal address.")
        else:
            embed = discord.Embed(color=0xe81111)
            embed.add_field(name='Error!', value="Please enter a valid TNBC account number.")

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="withdraw",
                            name="tnbc",
                            description="Withdraw TNBC into your account.",
                            options=[
                                create_option(
                                    name="amount",
                                    description="Enter the amount to withdraw.",
                                    option_type=4,
                                    required=True
                                )
                            ]
                            )
    async def user_withdraw(self, ctx, amount: int):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)
        tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

        if tnbc_wallet.withdrawal_address:

            response, fee = estimate_fee()

            if response:
                if not amount < 1:
                    if convert_to_int(tnbc_wallet.get_available_balance()) < amount + fee:
                        embed = discord.Embed(title="Inadequate Funds!",
                                              description=f"You only have {convert_to_int(tnbc_wallet.get_available_balance()) - fee} withdrawable TNBC (network fees included) available. \n Use `/deposit tnbc` to deposit TNBC.",
                                              color=0xe81111)

                    else:
                        block_response, fee = withdraw_tnbc(tnbc_wallet.withdrawal_address, amount, tnbc_wallet.memo)

                        if block_response:
                            if block_response.status_code == 201:
                                txs = Transaction.objects.create(confirmation_status=Transaction.WAITING_CONFIRMATION,
                                                                 transaction_status=Transaction.IDENTIFIED,
                                                                 direction=Transaction.OUTGOING,
                                                                 account_number=tnbc_wallet.withdrawal_address,
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
                                                      description=f"Successfully withdrawn {amount} TNBC to {tnbc_wallet.withdrawal_address} \n Use `/balance` to check your new balance.",
                                                      color=0xe81111)
                            else:
                                embed = discord.Embed(title="Error!", description="Please try again later.", color=0xe81111)
                        else:
                            embed = discord.Embed(title="Error!", description="Can not send transaction block to the bank, Try Again.", color=0xe81111)
                else:
                    embed = discord.Embed(title="Error!", description="You cannot withdraw less than 1 TNBC.", color=0xe81111)
            else:
                embed = discord.Embed(title="Error!", description="Could not load fee info from the bank.", color=0xe81111)
        else:
            embed = discord.Embed(title="No withdrawal address set!", description="Use `/set_withdrawal_address tnbc` to set withdrawal address.", color=0xe81111)

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

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(user.id)
        user_profile = get_or_create_user_profile(discord_user)

        embed = discord.Embed(title=f"{user.name}'s Crow Bot Profile", description="", color=0xe81111)
        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name='Total Trade(s)', value=user_profile.total_escrows)
        embed.add_field(name='Total Dispute(s)', value=user_profile.total_disputes)

        await ctx.send(embed=embed, hidden=True)

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

        else:
            embed = discord.Embed(title="Error!", description="404 Not Found.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_slash(name="guide", description="Check User Balance.")
    async def guide(self, ctx):

        await ctx.defer()

        embed = discord.Embed(color=0xe81111)
        embed.add_field(name="Seller Guide", value="[Youtube Tutorial](https://youtu.be/3WjW-i9neqI)", inline=False)
        embed.add_field(name="Buyer Guide", value="[Youtube Tutorial](https://youtu.be/yQyp6pZd2ys)")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(user(bot))
