import discord
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option
from core.utils.shortcuts import get_or_create_tnbc_wallet, get_or_create_discord_user
from discord_slash.utils.manage_components import create_button, create_actionrow
from django.conf import settings
from discord_slash.model import ButtonStyle
from core.utils.send_tnbc import estimate_fee, withdraw_tnbc
from core.models.transactions import Transaction
from core.models.statistics import Statistic
from core.models.users import UserTransactionHistory
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
        embed.add_field(name='Balance', value=tnbc_wallet.get_int_balance())
        embed.add_field(name='Locked Amount', value=tnbc_wallet.get_int_locked())
        embed.add_field(name='Available Balance', value=tnbc_wallet.get_int_available_balance())

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
                    if tnbc_wallet.get_int_available_balance() < amount + fee:
                        embed = discord.Embed(title="Inadequate Funds!",
                                              description=f"You only have {tnbc_wallet.get_int_available_balance() - fee} withdrawable TNBC (network fees included) available. \n Use `/deposit tnbc` to deposit TNBC.",
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

            embed.add_field(name='\u200b', value=f"{txs.type} - {txs.get_int_amount()} TNBC - {natural_day}", inline=False)

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
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(user(bot))
