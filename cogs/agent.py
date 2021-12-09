import discord
from discord.ext import commands

from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option, create_permission
from discord_slash.model import SlashCommandPermissionType

from django.conf import settings
from django.db.models import Q, F
from asgiref.sync import sync_to_async

from escrow.models.escrow import Escrow
from escrow.utils import get_or_create_user_profile, post_trade_to_api
from core.utils.shortcuts import convert_to_int, convert_to_decimal
from core.models.wallets import ThenewbostonWallet
from core.utils.shortcuts import get_or_create_discord_user
from core.models.statistics import Statistic


class agent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_subcommand(base="agent",
                            name="release",
                            description="Release the escrow to the buyer!",
                            options=[
                                create_option(
                                        name="escrow_id",
                                        description="Enter escrow id you want to cancel.",
                                        option_type=3,
                                        required=True
                                ),
                                create_option(
                                    name="remarks",
                                    description="Summary of the dispute.",
                                    option_type=3,
                                    required=True
                                )
                            ],
                            base_default_permission=False,
                            base_permissions={
                                int(settings.GUILD_ID): [
                                    create_permission(int(settings.AGENT_ROLE_ID), SlashCommandPermissionType.ROLE, True),
                                    create_permission(int(settings.GUILD_ID), SlashCommandPermissionType.ROLE, False)
                                ]
                            }
                            )
    async def agent_release(self, ctx, escrow_id: str, remarks: str):

        await ctx.defer(hidden=True)

        if int(settings.AGENT_ROLE_ID) in [y.id for y in ctx.author.roles]:

            if Escrow.objects.filter(Q(uuid_hex=escrow_id),
                                     Q(status=Escrow.DISPUTE)).exists():

                escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)
                discord_user = get_or_create_discord_user(ctx.author.id)
                escrow_obj.status = Escrow.ADMIN_SETTLED
                escrow_obj.agent = discord_user
                escrow_obj.remarks = remarks
                escrow_obj.save()

                ThenewbostonWallet.objects.filter(user=escrow_obj.initiator).update(balance=F('balance') - escrow_obj.amount, locked=F('locked') - escrow_obj.amount)
                ThenewbostonWallet.objects.filter(user=escrow_obj.successor).update(balance=F('balance') + escrow_obj.amount - escrow_obj.fee)

                statistic, created = Statistic.objects.get_or_create(title="main")
                statistic.total_fees_collected += escrow_obj.fee
                statistic.save()

                buyer_profile = get_or_create_user_profile(escrow_obj.successor)
                buyer_profile.total_escrows += 1
                buyer_profile.total_tnbc_escrowed += escrow_obj.amount - escrow_obj.fee
                buyer_profile.save()

                seller_profile = get_or_create_user_profile(escrow_obj.initiator)
                seller_profile.total_escrows += 1
                seller_profile.total_tnbc_escrowed += escrow_obj.amount
                seller_profile.save()

                embed = discord.Embed(title="Escrow Released Successfully", description="", color=0xe81111)
                embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
                embed.add_field(name='Amount', value=f"{convert_to_int(escrow_obj.amount)}")
                embed.add_field(name='Fee', value=f"{convert_to_int(escrow_obj.fee)}")
                embed.add_field(name='Status', value=f"{escrow_obj.status}")
                embed.add_field(name='Remarks', value=f"{escrow_obj.remarks}", inline=False)

                conversation_channel = self.bot.get_channel(int(escrow_obj.conversation_channel_id))
                await conversation_channel.send(embed=embed)

                recent_trade_channel = self.bot.get_channel(int(settings.RECENT_TRADE_CHANNEL_ID))

                await recent_trade_channel.send(f"Recent Trade: {convert_to_int(escrow_obj.amount)} TNBC at ${convert_to_decimal(escrow_obj.price)} each")

                post_trade_to_api(convert_to_int(escrow_obj.amount), escrow_obj.price)
                await ctx.guild.me.edit(nick=f"Price: {convert_to_decimal(escrow_obj.price)}")

            else:
                embed = discord.Embed(title="Error!", description="Disputed escrow not found.", color=0xe81111)
        else:
            embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="agent",
                            name="cancel",
                            description="Release the escrow back to seller.",
                            options=[
                                create_option(
                                    name="escrow_id",
                                    description="Enter escrow id you want to cancel.",
                                    option_type=3,
                                    required=True
                                ),
                                create_option(
                                    name="remarks",
                                    description="Summary of the escrow.",
                                    option_type=3,
                                    required=True
                                )
                            ]
                            )
    async def agent_cancel(self, ctx, escrow_id: str, remarks: str):

        await ctx.defer(hidden=True)

        if int(settings.AGENT_ROLE_ID) in [y.id for y in ctx.author.roles]:
            if Escrow.objects.filter(uuid_hex=escrow_id).exists():

                escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

                discord_user = get_or_create_discord_user(ctx.author.id)

                if escrow_obj.status == Escrow.DISPUTE:
                    escrow_obj.status = Escrow.ADMIN_CANCELLED
                    escrow_obj.remarks = remarks
                    escrow_obj.agent = discord_user
                    escrow_obj.save()

                    ThenewbostonWallet.objects.filter(user=escrow_obj.initiator).update(locked=F('locked') - escrow_obj.amount)

                    embed = discord.Embed(title="Escrow Cancelled Successfully", description="", color=0xe81111)
                    embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
                    embed.add_field(name='Amount', value=f"{convert_to_int(escrow_obj.amount)}")
                    embed.add_field(name='Fee', value=f"{convert_to_int(escrow_obj.fee)}")
                    embed.add_field(name='Status', value=f"{escrow_obj.status}")

                    conversation_channel = self.bot.get_channel(int(escrow_obj.conversation_channel_id))
                    await conversation_channel.send(embed=embed)

                else:
                    embed = discord.Embed(title="Error!", description=f"You cannot cancel the escrow of status {escrow_obj.status}.", color=0xe81111)
            else:
                embed = discord.Embed(title="Error!", description="404 Not Found.", color=0xe81111)
        else:
            embed = discord.Embed(title="Error!", description="You donot have permission to perform this action.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)


def setup(bot):
    bot.add_cog(agent(bot))
