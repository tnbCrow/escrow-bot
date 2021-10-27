import discord
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option
from django.conf import settings
from asgiref.sync import sync_to_async
from django.db.models import Q

from escrow.models.escrow import Escrow
from core.models.users import UserTransactionHistory
from core.utils.shortcuts import get_or_create_discord_user, get_or_create_tnbc_wallet, convert_to_decimal


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
                            ]
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
                    embed.add_field(name='Amount', value=f"{escrow.get_int_amount()}")
                    embed.add_field(name='Fee', value=f"{escrow.get_int_fee()}")
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
            embed.add_field(name='Balance', value=tnbc_wallet.get_int_balance())
            embed.add_field(name='Locked Amount', value=tnbc_wallet.get_int_locked())
            embed.add_field(name='Available Balance', value=tnbc_wallet.get_int_available_balance())

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

            UserTransactionHistory.objects.create(user=discord_user, type=UserTransactionHistory.DEPOSIT, amount=amount)

            embed = discord.Embed(color=0xe81111)
            embed.add_field(name='Success', value=f"Refunded {convert_to_decimal(amount)} to the user.")
            embed.add_field(name='Withdrawal Address', value=tnbc_wallet.withdrawal_address, inline=False)
            embed.add_field(name='Balance', value=tnbc_wallet.get_int_balance())
            embed.add_field(name='Locked Amount', value=tnbc_wallet.get_int_locked())
            embed.add_field(name='Available Balance', value=tnbc_wallet.get_int_available_balance())

        else:
            embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)


def setup(bot):
    bot.add_cog(admin(bot))
