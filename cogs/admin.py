import discord
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option, create_permission
from discord_slash.model import SlashCommandPermissionType

from django.conf import settings
from asgiref.sync import sync_to_async
from django.db.models import Q

from core.models.transactions import Transaction
from core.models.wallets import ThenewbostonWallet
from core.models.users import UserTransactionHistory
from core.models.statistics import Statistic
from core.utils.shortcuts import convert_to_int, get_or_create_discord_user, get_or_create_tnbc_wallet, convert_to_decimal, get_wallet_balance
from core.utils.send_tnbc import estimate_fee, withdraw_tnbc

from escrow.models.escrow import Escrow
from escrow.utils import get_total_balance_of_all_user, post_trade_to_api, create_offer_table
from escrow.models.advertisement import Advertisement


class admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_subcommand(base="admin",
                            name="escrows",
                            description="Check the ongoing escrows of the user!",
                            options=[
                                create_option(
                                    name="user",
                                    description="User you want to check the escrows of.",
                                    option_type=6,
                                    required=True
                                )
                            ],
                            base_default_permission=False,
                            base_permissions={
                                int(settings.GUILD_ID): [
                                    create_permission(int(settings.ADMIN_ROLE_ID), SlashCommandPermissionType.ROLE, True),
                                    create_permission(int(settings.GUILD_ID), SlashCommandPermissionType.ROLE, False)
                                ]
                            }
                            )
    async def admin_escrows(self, ctx, user):

        await ctx.defer(hidden=True)

        if int(settings.ADMIN_ROLE_ID) in [y.id for y in ctx.author.roles]:

            discord_user = get_or_create_discord_user(user.id)

            if Escrow.objects.filter(Q(initiator=discord_user) | Q(successor=discord_user)).exists():
                escrows = (await sync_to_async(Escrow.objects.filter)(Q(initiator=discord_user) | Q(successor=discord_user))).order_by('-updated_at')[:4]

                embed = discord.Embed(color=0xe81111)

                for escrow in escrows:

                    embed.add_field(name='ID', value=f"{escrow.uuid_hex}", inline=False)
                    embed.add_field(name='Amount', value=f"{convert_to_int(escrow.amount)}")
                    embed.add_field(name='Fee', value=f"{convert_to_int(escrow.fee)}")
                    embed.add_field(name='Status', value=f"{escrow.status}")
                    if discord_user == escrow.successor:
                        initiator = await self.bot.fetch_user(int(escrow.initiator.discord_id))
                        embed.add_field(name='Role', value='Buyer')
                        embed.add_field(name='Seller', value=f"{initiator.mention}")
                    else:
                        successor = await self.bot.fetch_user(int(escrow.successor.discord_id))
                        embed.add_field(name='Role', value='Seller')
                        embed.add_field(name='Buyer', value=f"{successor.mention}")

            else:
                embed = discord.Embed(title="Oops..", description="No active escrows found.", color=0xe81111)

        else:
            embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="admin",
                            name="escrow_history",
                            description="Check all ongoing/ completed escrows!",
                            )
    async def admin_escrow_history(self, ctx):

        await ctx.defer(hidden=True)

        if int(settings.ADMIN_ROLE_ID) in [y.id for y in ctx.author.roles]:

            escrows = (await sync_to_async(Escrow.objects.all)()).order_by('-updated_at')[:4]

            embed = discord.Embed(color=0xe81111)

            for escrow in escrows:

                initiator = await self.bot.fetch_user(int(escrow.initiator.discord_id))
                successor = await self.bot.fetch_user(int(escrow.successor.discord_id))

                embed.add_field(name='ID', value=f"{escrow.uuid_hex}", inline=False)
                embed.add_field(name='Amount', value=f"{convert_to_int(escrow.amount)}")
                embed.add_field(name='Fee', value=f"{convert_to_int(escrow.fee)}")
                embed.add_field(name='Buyer', value=f"{successor.mention}")
                embed.add_field(name='Seller', value=f"{initiator.mention}")
                embed.add_field(name='Status', value=f"{escrow.status}")

        else:
            embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="admin",
                            name="balance",
                            description="Check the balance of the user!",
                            options=[
                                create_option(
                                    name="user",
                                    description="User you want to check the balance of.",
                                    option_type=6,
                                    required=True
                                )
                            ]
                            )
    async def admin_balance(self, ctx, user):

        await ctx.defer(hidden=True)

        if int(settings.ADMIN_ROLE_ID) in [y.id for y in ctx.author.roles]:

            discord_user = get_or_create_discord_user(user.id)
            tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

            embed = discord.Embed(color=0xe81111)
            embed.add_field(name='Withdrawal Address', value=tnbc_wallet.withdrawal_address, inline=False)
            embed.add_field(name='Balance', value=convert_to_int(tnbc_wallet.balance))
            embed.add_field(name='Locked Amount', value=convert_to_int(tnbc_wallet.locked))
            embed.add_field(name='Available Balance', value=convert_to_int(tnbc_wallet.get_available_balance()))

        else:
            embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="admin",
                            name="refund",
                            description="Refund TNBC to user!",
                            options=[
                                create_option(
                                    name="user",
                                    description="User to whom you have to refund.",
                                    option_type=6,
                                    required=True
                                ),
                                create_option(
                                    name="amount",
                                    description="Enter TNBC amount you want to refund.",
                                    option_type=4,
                                    required=True
                                ),
                            ]
                            )
    async def admin_refund(self, ctx, user, amount: int):

        await ctx.defer(hidden=True)

        if int(settings.ADMIN_ROLE_ID) in [y.id for y in ctx.author.roles]:

            discord_user = get_or_create_discord_user(user.id)
            tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

            amount = amount * settings.TNBC_MULTIPLICATION_FACTOR

            tnbc_wallet.balance += amount
            tnbc_wallet.save()

            UserTransactionHistory.objects.create(user=discord_user, type=UserTransactionHistory.REFUND, amount=amount)

            statistic, created = Statistic.objects.get_or_create(title="main")
            statistic.total_balance += amount
            statistic.save()

            embed = discord.Embed(color=0xe81111)
            embed.add_field(name='Success', value=f"Refunded {convert_to_decimal(amount)} to the user.")
            embed.add_field(name='Withdrawal Address', value=tnbc_wallet.withdrawal_address, inline=False)
            embed.add_field(name='Balance', value=convert_to_int(tnbc_wallet.balance))
            embed.add_field(name='Locked Amount', value=convert_to_int(tnbc_wallet.locked))
            embed.add_field(name='Available Balance', value=convert_to_int(tnbc_wallet.get_available_balance()))

        else:
            embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="admin",
                            name="takeback",
                            description="Takeback TNBC from the user!",
                            options=[
                                create_option(
                                    name="user",
                                    description="User from whom you have to take back TNBC.",
                                    option_type=6,
                                    required=True
                                ),
                                create_option(
                                    name="amount",
                                    description="Enter TNBC amount you want to take back.",
                                    option_type=4,
                                    required=True
                                ),
                            ]
                            )
    async def admin_takeback(self, ctx, user, amount: int):

        await ctx.defer(hidden=True)

        if int(settings.ADMIN_ROLE_ID) in [y.id for y in ctx.author.roles]:

            discord_user = get_or_create_discord_user(user.id)
            tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

            amount = amount * settings.TNBC_MULTIPLICATION_FACTOR

            if amount <= tnbc_wallet.get_available_balance():

                tnbc_wallet.balance -= amount
                tnbc_wallet.save()

                UserTransactionHistory.objects.create(user=discord_user, type=UserTransactionHistory.TAKEBACK, amount=amount)

                statistic, created = Statistic.objects.get_or_create(title="main")
                statistic.total_balance -= amount
                statistic.save()

                embed = discord.Embed(color=0xe81111)
                embed.add_field(name='Success', value=f"Takeback {convert_to_decimal(amount)} to the user.")
                embed.add_field(name='Withdrawal Address', value=tnbc_wallet.withdrawal_address, inline=False)
                embed.add_field(name='Balance', value=convert_to_int(tnbc_wallet.balance))
                embed.add_field(name='Locked Amount', value=convert_to_int(tnbc_wallet.locked))
                embed.add_field(name='Available Balance', value=convert_to_int(tnbc_wallet.get_available_balance()))

            else:
                embed = discord.Embed(title="Error!", description="The user does not have enough TNBC in their wallet to take back.", color=0xe81111)

        else:
            embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="admin",
                            name="stats",
                            description="Check the statistics of the bot!")
    async def admin_stats(self, ctx):

        await ctx.defer(hidden=True)

        if int(settings.ADMIN_ROLE_ID) in [y.id for y in ctx.author.roles]:

            statistic, created = Statistic.objects.get_or_create(title="main")

            hot_wallet_balance = get_wallet_balance(settings.TNBCROW_BOT_ACCOUNT_NUMBER)
            cold_wallet_balance = get_wallet_balance(settings.COLD_WALLET_ACCOUNT_NUMBER)
            wallet_balance_combined = hot_wallet_balance + cold_wallet_balance

            balance_of_all_user = get_total_balance_of_all_user()

            embed = discord.Embed(color=0xe81111)
            embed.add_field(name='Total Balance', value=convert_to_int(statistic.total_balance))
            embed.add_field(name='User Balance + Fees Collected', value=convert_to_int(balance_of_all_user + statistic.total_fees_collected))
            embed.add_field(name='Hot Wallet Balance', value=hot_wallet_balance)
            embed.add_field(name='Cold Wallet Balance', value=cold_wallet_balance)
            embed.add_field(name='Total Wallet Balance', value=wallet_balance_combined)
            embed.add_field(name='Fees Collected', value=convert_to_decimal(statistic.total_fees_collected))

        else:
            embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="admin",
                            name="transactions_unconfirmed",
                            description="Check the statistics of the bot!")
    async def admin_transactions_unconfirmed(self, ctx):

        await ctx.defer(hidden=True)

        if int(settings.ADMIN_ROLE_ID) in [y.id for y in ctx.author.roles]:

            if Transaction.objects.filter(Q(direction=Transaction.INCOMING) & Q(confirmation_status=Transaction.WAITING_CONFIRMATION) | Q(transaction_status=Transaction.UNIDENTIFIED)).exists():

                unconfirmed_transactions = (await sync_to_async(Transaction.objects.filter)(Q(direction=Transaction.INCOMING) & Q(confirmation_status=Transaction.WAITING_CONFIRMATION) | Q(transaction_status=Transaction.UNIDENTIFIED))).order_by('-created_at')[:4]

                embed = discord.Embed(color=0xe81111)
                for transaction in unconfirmed_transactions:

                    embed.add_field(name='ID', value=transaction.uuid, inline=False)
                    embed.add_field(name='Signature', value=transaction.signature, inline=False)
                    embed.add_field(name='Block', value=transaction.block, inline=False)
                    embed.add_field(name='Amount', value=convert_to_int(transaction.amount))

                    if transaction.memo:
                        embed.add_field(name='MEMO', value=transaction.memo)
                    else:
                        embed.add_field(name='MEMO', value="Null")

                    if ThenewbostonWallet.objects.filter(memo=transaction.memo).exists():
                        user_wallet = ThenewbostonWallet.objects.get(memo=transaction.memo)
                        discord_user = await self.bot.fetch_user(int(user_wallet.user.discord_id))
                        embed.add_field(name='User', value=discord_user.mention)
                    else:
                        embed.add_field(name='User', value="Unidentified")
            else:
                embed = discord.Embed(title="404", description="Unconfirmed transactions not found.", color=0xe81111)

        else:
            embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="admin",
                            name="deposit",
                            description="Add deposit to user's account!",
                            options=[
                                create_option(
                                    name="user",
                                    description="User you want to add deposit of.",
                                    option_type=6,
                                    required=True
                                ),
                                create_option(
                                    name="transaction_id",
                                    description="UUID of unconfirmed transaction.",
                                    option_type=3,
                                    required=True
                                ),
                            ])
    async def admin_deposit(self, ctx, user: discord.Member, transaction_id: str):

        await ctx.defer(hidden=True)

        if int(settings.ADMIN_ROLE_ID) in [y.id for y in ctx.author.roles]:

            if Transaction.objects.filter(Q(uuid=transaction_id) & Q(direction=Transaction.INCOMING) & Q(confirmation_status=Transaction.WAITING_CONFIRMATION) | Q(transaction_status=Transaction.UNIDENTIFIED)).exists():

                transaction = Transaction.objects.get(uuid=transaction_id)
                transaction.confirmation_status = Transaction.CONFIRMED
                transaction.transaction_status = Transaction.IDENTIFIED
                transaction.save()

                discord_user = get_or_create_discord_user(user.id)
                wallet = get_or_create_tnbc_wallet(discord_user)
                wallet.balance += transaction.amount
                wallet.save()

                statistics, created = Statistic.objects.get_or_create(title="main")
                statistics.total_balance += transaction.amount
                statistics.save()

                UserTransactionHistory.objects.create(user=discord_user, amount=transaction.amount, type=UserTransactionHistory.DEPOSIT, transaction=transaction)

                embed = discord.Embed(color=0xe81111)
                embed = discord.Embed(title="Success!", description=f"Linked transaction with id `{transaction_id}` with user {user.mention}.", color=0xe81111)

            else:
                embed = discord.Embed(title="Error!", description="The transaction incoming with waiting confirmation status does not exist.", color=0xe81111)

        else:
            embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="admin",
                            name="transfer_to_cold_wallet",
                            description="Transfer TNBC from Hot to Cold wallet!",
                            options=[
                                create_option(
                                    name="amount",
                                    description="Enter TNBC amount you want to transfer.",
                                    option_type=4,
                                    required=True
                                ),
                            ]
                            )
    async def admin_transfer_to_cold_wallet(self, ctx, amount: int):

        await ctx.defer(hidden=True)

        if int(settings.ADMIN_ROLE_ID) in [y.id for y in ctx.author.roles]:
            response, fee = estimate_fee()

            if response:
                if not amount < 1:
                    hot_wallet_balance = get_wallet_balance(settings.TNBCROW_BOT_ACCOUNT_NUMBER)
                    if hot_wallet_balance >= amount + fee:

                        block_response, fee = withdraw_tnbc(settings.COLD_WALLET_ACCOUNT_NUMBER, amount, "INTERNAL")

                        if block_response:
                            if block_response.status_code == 201:
                                Transaction.objects.create(confirmation_status=Transaction.WAITING_CONFIRMATION,
                                                           transaction_status=Transaction.IDENTIFIED,
                                                           direction=Transaction.OUTGOING,
                                                           account_number=settings.COLD_WALLET_ACCOUNT_NUMBER,
                                                           amount=amount * settings.TNBC_MULTIPLICATION_FACTOR,
                                                           fee=fee * settings.TNBC_MULTIPLICATION_FACTOR,
                                                           signature=block_response.json()['signature'],
                                                           block=block_response.json()['id'],
                                                           memo="INTERNAL")

                                statistic, created = Statistic.objects.get_or_create(title="main")
                                statistic.total_balance -= fee * settings.TNBC_MULTIPLICATION_FACTOR
                                statistic.save()

                                embed = discord.Embed(title="Coins Withdrawn.",
                                                      description=f"Successfully withdrawn {amount} TNBC to the cold wallet.",
                                                      color=0xe81111)
                            else:
                                embed = discord.Embed(title="Error!", description="Please try again later.", color=0xe81111)
                        else:
                            embed = discord.Embed(title="Error!", description="Can not send transaction block to the bank, Try Again.", color=0xe81111)
                    else:
                        embed = discord.Embed(title="Error!", description="Not enough TNBC available in the hot wallet.", color=0xe81111)
                else:
                    embed = discord.Embed(title="Error!", description="You cannot withdraw less than 1 TNBC.", color=0xe81111)
            else:
                embed = discord.Embed(title="Error!", description="Could not load fee info from the bank.", color=0xe81111)
        else:
            embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="admin",
                            name="adv_status",
                            description="Check the status of particular advertisement.",
                            options=[
                                create_option(
                                    name="advertisement_id",
                                    description="Enter the advertisement id you want to check the status of.",
                                    option_type=3,
                                    required=True
                                )
                            ]
                            )
    async def admin_adv_status(self, ctx, advertisement_id: str):

        await ctx.defer(hidden=True)

        if int(settings.ADMIN_ROLE_ID) in [y.id for y in ctx.author.roles]:

            if Advertisement.objects.filter(uuid_hex=advertisement_id).exists():

                advertisement = await sync_to_async(Advertisement.objects.get)(uuid_hex=advertisement_id)

                adv_owner = await self.bot.fetch_user(int(advertisement.owner.discord_id))

                embed = discord.Embed(color=0xe81111)
                embed.add_field(name='ID', value=f"{advertisement.uuid_hex}", inline=False)
                embed.add_field(name='Amount', value=convert_to_int(advertisement.amount))
                embed.add_field(name='Price Per TNBC (USDT)', value=convert_to_decimal(advertisement.price))
                embed.add_field(name="Owner", value=adv_owner.mention, inline=False)

            else:
                embed = discord.Embed(title="Error!", description="404 Not Found.", color=0xe81111)
        else:
            embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="admin",
                            name="add_verified_trade",
                            description="Add verified trade.",
                            options=[
                                create_option(
                                    name="amount",
                                    description="Amount of TNBC that was traded.",
                                    option_type=4,
                                    required=True
                                ),
                                create_option(
                                    name="price",
                                    description="The rate at which it was traded for.",
                                    option_type=10,
                                    required=True
                                ),
                                create_option(
                                    name="payment_method",
                                    description="The payment method that was used to carry out trade.",
                                    option_type=3,
                                    required=True
                                )
                            ]
                            )
    async def admin_add_verified_trade(self, ctx, amount: int, price: float, payment_method: str):

        await ctx.defer(hidden=True)

        if int(settings.ADMIN_ROLE_ID) in [y.id for y in ctx.author.roles]:

            recent_trade_channel = self.bot.get_channel(int(settings.RECENT_TRADE_CHANNEL_ID))

            success = post_trade_to_api(amount, price * 10000)

            if success:
                comma_seperated_amount = "{:,}".format(amount)
                await recent_trade_channel.send(f"Verified Trade: {comma_seperated_amount} TNBC at {price} each. Payment Method: {payment_method}")
                await ctx.guild.me.edit(nick=f"Price: {price} USDC")
                embed = discord.Embed(title="Success!", description="Posted trade successfully.", color=0xe81111)
            else:
                embed = discord.Embed(title="Error!", description="Could not post the trade to API.", color=0xe81111)
        else:
            embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="admin",
                            name="remove_buy_adv",
                            description="The buy advertisement that you want to remove.",
                            options=[
                                create_option(
                                    name="advertisement_id",
                                    description="Enter the advertisement id you want to check the status of.",
                                    option_type=3,
                                    required=True
                                )
                            ]
                            )
    async def admin_remove_buy_adv(self, ctx, advertisement_id: str):

        await ctx.defer(hidden=True)

        if int(settings.ADMIN_ROLE_ID) in [y.id for y in ctx.author.roles]:

            if Advertisement.objects.filter(uuid_hex=advertisement_id, side=Advertisement.BUY).exists():
                Advertisement.objects.filter(uuid_hex=advertisement_id).delete()
                buy_offer_channel = self.bot.get_channel(int(settings.TRADE_CHANNEL_ID))
                offer_table = create_offer_table(Advertisement.BUY, 20)

                async for oldMessage in buy_offer_channel.history():
                    await oldMessage.delete()
                await buy_offer_channel.send(f"**Buy Advertisements.**\nUse `/guide buyer` command for the buyer's guide and `/guide seller` for seller's guide to trade on tnbCrow discord server.\n```{offer_table}```")
                embed = discord.Embed(title="Success!", description="Advertisement removed successfully.", color=0xe81111)
            else:
                embed = discord.Embed(title="Error!", description="The buy advertisement your're tryig to delete does not exist.", color=0xe81111)
        else:
            embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="admin",
                            name="commands",
                            description="List of all admin commands.")
    async def admin_commands(self, ctx):

        await ctx.defer(hidden=True)

        if int(settings.ADMIN_ROLE_ID) in [y.id for y in ctx.author.roles]:
            embed = discord.Embed(color=0xe81111)
            embed.add_field(name='/admin balance user: USER', value=f"Check the balance statistics of particular user.", inline=False)
            embed.add_field(name='/admin escrows user: USER', value=f"Check escrows of particular user.", inline=False)
            embed.add_field(name='/admin escrow_history', value=f"Check the escrow history of the bot.", inline=False)
            embed.add_field(name='/admin stats', value=f"Check the statistics of bot.", inline=False)
            embed.add_field(name='/admin transactions_unconfirmed', value=f"Check all unconfirmed transactions.", inline=False)
            embed.add_field(name='/admin deposit user: USER', value=f"Check unconfirmed transaction to user.", inline=False)
            embed.add_field(name='/admin adv_status advertisement_id: ID', value=f"Check all advertisement details.", inline=False)
            embed.add_field(name='/admin add_verified_trade amount: AMOUNT price: PRICE payment_method: METHOD', value=f"Add a verifed trade.", inline=False)
            embed.add_field(name='/admin remove_buy_adv advertisement_id: ID', value=f"Delete a buy advertisement.", inline=False)
        else:
            embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.", color=0xe81111)
        await ctx.send(embed=embed, hidden=True)

def setup(bot):
    bot.add_cog(admin(bot))
