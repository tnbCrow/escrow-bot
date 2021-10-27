import discord
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option
from core.utils.shortcuts import get_or_create_discord_user
from django.conf import settings
from asgiref.sync import sync_to_async
from escrow.models.escrow import Escrow
from django.db.models import Q


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
                    if escrow.initiator == discord_user:
                        embed.add_field(name='Role', value="Seller")
                    else:
                        embed.add_field(name='Role', value="Buyer")

            else:
                embed = discord.Embed(title="Oops..", description="No active escrows found.", color=0xe81111)

        else:
            embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

def setup(bot):
    bot.add_cog(admin(bot))
