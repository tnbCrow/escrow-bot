import discord
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option, create_permission
from discord_slash.model import SlashCommandPermissionType

from django.conf import settings
from asgiref.sync import sync_to_async
from django.db.models import Q

from escrow.models.escrow import Escrow
from core.models.users import UserTransactionHistory
from core.models.statistics import Statistic
from core.utils.shortcuts import convert_to_int, get_or_create_discord_user, get_or_create_tnbc_wallet, convert_to_decimal, get_wallet_balance


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

            if Escrow.objects.filter(Q(initiator=discord_user) | Q(successor=discord_user), Q(status=Escrow.OPEN) | Q(status=Escrow.DISPUTE)).exists():
                escrows = await sync_to_async(Escrow.objects.filter)(Q(initiator=discord_user) | Q(successor=discord_user), Q(status=Escrow.OPEN) | Q(status=Escrow.DISPUTE))

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
            embed.add_field(name='Locked Amount', value=convert_to_int(tnbc_wallet.total_balance)(tnbc_wallet.locked))
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

            wallet_balance = get_wallet_balance()

            embed = discord.Embed(color=0xe81111)
            embed.add_field(name='Total Balance', value=convert_to_decimal(statistic.total_balance))
            embed.add_field(name='Wallet Balance', value=wallet_balance)
            embed.add_field(name='Fees Collected', value=convert_to_decimal(statistic.total_fees_collected), inline=False)

        else:
            embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)


def setup(bot):
    bot.add_cog(admin(bot))
