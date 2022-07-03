import discord
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option
from discord_slash.utils.manage_components import create_button, create_actionrow
from discord_slash.model import ButtonStyle
from django.conf import settings
from django.db.models import Q
from asgiref.sync import sync_to_async

from core.utils.shortcuts import get_or_create_discord_user
from core.utils.logger import log_send
from core.utils.shortcuts import convert_to_decimal, get_or_create_tnbc_wallet, comma_seperated_int

from escrow.models.escrow import Escrow
from escrow.models.advertisement import Advertisement
from escrow.utils import get_or_create_user_profile, create_offer_table


class escrow(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_subcommand(base="escrow",
                            name="status",
                            description="Escrow Leap Coin with another user.",
                            options=[
                                create_option(
                                    name="escrow_id",
                                    description="Enter escrow id you want to check the status of.",
                                    option_type=3,
                                    required=True
                                )
                            ]
                            )
    async def escrow_status(self, ctx, escrow_id: str):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)

        if Escrow.objects.filter(Q(initiator=discord_user) | Q(successor=discord_user), Q(uuid_hex=escrow_id)).exists():
            escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

            embed = discord.Embed(color=0xe81111)
            embed.add_field(name='Escrow ID', value=f"{escrow_obj.uuid_hex}", inline=False)
            embed.add_field(name='Amount', value=f"{comma_seperated_int(escrow_obj.amount)} Leap Coin")
            embed.add_field(name='Fee', value=f"{comma_seperated_int(escrow_obj.fee)} Leap Coin")
            embed.add_field(name='Buyer Receives', value=f"{comma_seperated_int(escrow_obj.amount - escrow_obj.fee)} Leap Coin")
            embed.add_field(name='Price (USDT)', value=convert_to_decimal(escrow_obj.price))
            if discord_user == escrow_obj.successor:
                initiator = await self.bot.fetch_user(int(escrow_obj.initiator.discord_id))
                embed.add_field(name='Your Role', value='Buyer')
                embed.add_field(name='Seller', value=f"{initiator.mention}")
            else:
                successor = await self.bot.fetch_user(int(escrow_obj.successor.discord_id))
                embed.add_field(name='Your Role', value='Seller')
                embed.add_field(name='Buyer', value=f"{successor.mention}")

            embed.add_field(name='Status', value=f"{escrow_obj.status}")

            if escrow_obj.status == Escrow.ADMIN_SETTLED or escrow_obj.status == Escrow.ADMIN_CANCELLED:
                embed.add_field(name='Settled Towards', value=f"{escrow_obj.settled_towards}")
                embed.add_field(name='Remarks', value=f"{escrow_obj.remarks}", inline=False)

        else:
            embed = discord.Embed(title="Error!", description="404 Not Found.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="escrow", name="all", description="All your active escrows.")
    async def escrow_all(self, ctx):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)

        if Escrow.objects.filter(Q(initiator=discord_user) | Q(successor=discord_user), Q(status=Escrow.OPEN) | Q(status=Escrow.DISPUTE)).exists():
            escrows = (await sync_to_async(Escrow.objects.filter)(Q(initiator=discord_user) | Q(successor=discord_user), Q(status=Escrow.OPEN) | Q(status=Escrow.DISPUTE))).order_by('-updated_at')[:5]

            embed = discord.Embed(color=0xe81111)

            for escrow in escrows:

                embed.add_field(name='Escrow ID', value=f"{escrow.uuid_hex}", inline=False)
                embed.add_field(name='Amount', value=f"{comma_seperated_int(escrow.amount)} Leap Coin")

                if escrow.side == Escrow.BUY:
                    embed.add_field(name='Seller Pays', value=f"{comma_seperated_int(escrow.amount + escrow.fee)} Leap Coin")
                    embed.add_field(name='Buyer Receives', value=f"{comma_seperated_int(escrow.amount)} Leap Coin")
                else:
                    embed.add_field(name='Fee', value=f"{comma_seperated_int(escrow.fee)} Leap Coin")
                    embed.add_field(name='Buyer Receives', value=f"{comma_seperated_int(escrow.amount - escrow.fee)} Leap Coin")

                embed.add_field(name='Price (USDT)', value=convert_to_decimal(escrow.price))
                embed.add_field(name='Status', value=f"{escrow.status}")
                embed.set_footer(text="Use /escrow release to release the Leap Coin once you've received payment or /escrow cancel to cancel the escrow.")

                if discord_user == escrow.successor:
                    initiator = await self.bot.fetch_user(int(escrow.initiator.discord_id))
                    embed.add_field(name='Seller', value=f"{initiator.mention}")
                else:
                    successor = await self.bot.fetch_user(int(escrow.successor.discord_id))
                    embed.add_field(name='Buyer', value=f"{successor.mention}")
        else:
            embed = discord.Embed(title="Oops..", description="No active escrows found.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="escrow",
                            name="release",
                            description="Release escrow to successor.",
                            options=[
                                create_option(
                                    name="escrow_id",
                                    description="Enter escrow id you want to check the status of.",
                                    option_type=3,
                                    required=True
                                )
                            ]
                            )
    async def escrow_release(self, ctx, escrow_id: str):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)

        if Escrow.objects.filter(uuid_hex=escrow_id, initiator=discord_user).exists():

            escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

            if escrow_obj.status == Escrow.OPEN:

                warning_message = "**Warning**\nNever release the escrow before verifying that you've received the payment. Do you confirm that you've received payment from the buyer?"

                await ctx.send(warning_message,
                               hidden=True,
                               components=[
                                   create_actionrow(
                                       create_button(
                                           custom_id=f"escrowrelease_{escrow_id}",
                                           style=ButtonStyle.red,
                                           label="I have received payment, Release Escrow."),
                                       create_button(
                                           custom_id="escrowreleaseforbid",
                                           style=ButtonStyle.green,
                                           label="I have not received the payment, take me back.")
                                   )
                               ])

            else:
                embed = discord.Embed(title="Error!", description=f"You cannot release the escrow of status {escrow_obj.status}.", color=0xe81111)
                await ctx.send(embed=embed, hidden=True)
        else:
            embed = discord.Embed(title="Error!", description="You do not have permission to perform the action.", color=0xe81111)
            await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="escrow",
                            name="cancel",
                            description="Cancel escrow.",
                            options=[
                                create_option(
                                    name="escrow_id",
                                    description="Enter escrow id you want to check the status of.",
                                    option_type=3,
                                    required=True
                                )
                            ]
                            )
    async def escrow_cancel(self, ctx, escrow_id: str):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)

        if Escrow.objects.filter(Q(initiator=discord_user) |
                                 Q(successor=discord_user),
                                 Q(uuid_hex=escrow_id)).exists():

            escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

            if escrow_obj.status == Escrow.NEW:

                escrow_obj.status = Escrow.CANCELLED
                escrow_obj.save()

                sell_advertisement, created = Advertisement.objects.get_or_create(owner=escrow_obj.initiator, price=escrow_obj.price, side=Advertisement.SELL, defaults={'amount': 0})
                sell_advertisement.amount += escrow_obj.amount
                sell_advertisement.status = Advertisement.OPEN
                sell_advertisement.save()

                sell_order_channel = self.bot.get_channel(int(settings.OFFER_CHANNEL_ID))
                offers = create_offer_table(Advertisement.SELL, 16)

                async for oldMessage in sell_order_channel.history():
                    await oldMessage.delete()

                await sell_order_channel.send("**Sell Advertisements**")
                for offer in offers:
                    await sell_order_channel.send(f"```{offer}```")
                await sell_order_channel.send("Use the command `/adv buy advertisement_id: ID amount: AMOUNT` to buy Leap Coin from the above advertisements.\nOr `/adv create` to create your own buy/ sell advertisement.")

                await log_send(bot=self.bot, message=f"{ctx.author.mention} just cancelled the escrow. Escrow ID: {escrow_obj.uuid_hex}. Sell Adv Id: {sell_advertisement.uuid_hex}")

                embed = discord.Embed(title="Escrow Cancelled Successfully", description="", color=0xe81111)
                embed.add_field(name='Escrow ID', value=f"{escrow_obj.uuid_hex}", inline=False)
                embed.add_field(name='Amount', value=f"{comma_seperated_int(escrow_obj.amount)} Leap Coin")
                embed.add_field(name='Fee', value=f"{comma_seperated_int(escrow_obj.fee)} Leap Coin")
                embed.add_field(name='Price (USDT)', value=convert_to_decimal(escrow_obj.price))
                embed.add_field(name='Status', value=f"{escrow_obj.status}")

                conversation_channel = self.bot.get_channel(int(escrow_obj.conversation_channel_id))
                if conversation_channel:
                    await conversation_channel.send(embed=embed)

                embed = discord.Embed(title="Success!", description="Escrow cancelled successfully.", color=0xe81111)
                await ctx.send(embed=embed, hidden=True)

            elif escrow_obj.status == Escrow.OPEN:

                if int(escrow_obj.successor.discord_id) == ctx.author.id:

                    warning_message = "**Warning**\nNever cancel the escrow if you've sent the payment already. Do you confirm that you've not sent any payment to the seller?"

                    await ctx.send(warning_message,
                                   hidden=True,
                                   components=[
                                       create_actionrow(
                                           create_button(
                                               custom_id=f"escrowcancel_{escrow_id}",
                                               style=ButtonStyle.red,
                                               label="I have not paid on this trade, Cancel Trade."),
                                           create_button(
                                               custom_id="escrowcancelforbid",
                                               style=ButtonStyle.green,
                                               label="I've made the payment already, take me back.")
                                       )
                                   ])
                else:
                    embed = discord.Embed(title="Error!", description="Only the buyer can cancel the escrow. Use the command /escrow dispute if they're not responding.", color=0xe81111)
                    await ctx.send(embed=embed, hidden=True)
            else:
                embed = discord.Embed(title="Error!", description=f"You cannot cancel the escrow of status {escrow_obj.status}.", color=0xe81111)
                await ctx.send(embed=embed, hidden=True)
        else:
            embed = discord.Embed(title="Error!", description="404 Not Found.", color=0xe81111)
            await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="escrow",
                            name="fund",
                            description="Fund an escrow.",
                            options=[
                                create_option(
                                    name="escrow_id",
                                    description="Enter escrow id you want to fund.",
                                    option_type=3,
                                    required=True
                                )
                            ]
                            )
    async def escrow_fund(self, ctx, escrow_id: str):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)

        if Escrow.objects.filter(Q(initiator=discord_user),
                                 Q(uuid_hex=escrow_id)).exists():

            escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

            if escrow_obj.side == Escrow.SELL:

                if escrow_obj.status == Escrow.NEW:

                    seller_tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

                    if seller_tnbc_wallet.get_available_balance() >= escrow_obj.amount:

                        seller_tnbc_wallet.locked += escrow_obj.amount
                        seller_tnbc_wallet.save()

                        escrow_obj.status = Escrow.OPEN
                        escrow_obj.save()

                        embed = discord.Embed(title="Escrow Funded Successfully", description="", color=0xe81111)
                        embed.add_field(name='Escrow ID', value=f"{escrow_obj.uuid_hex}", inline=False)
                        embed.add_field(name='Amount', value=f"{comma_seperated_int(escrow_obj.amount)} Leap Coin")
                        embed.add_field(name='Fee', value=f"{comma_seperated_int(escrow_obj.fee)} Leap Coin")
                        embed.add_field(name='Price (USDT)', value=convert_to_decimal(escrow_obj.price))
                        embed.add_field(name='Status', value=f"{escrow_obj.status}")

                        conversation_channel = self.bot.get_channel(int(escrow_obj.conversation_channel_id))

                        if conversation_channel:
                            buyer = await self.bot.fetch_user(int(escrow_obj.successor.discord_id))
                            await conversation_channel.send(embed=embed)
                            await conversation_channel.send(
                                f"{buyer.mention}, escrow is funded successfully. "
                                f"You can now transfer payment to the seller.\n\n"
                                f"{buyer.mention}, please use the command `/escrow paid escrow_id: {escrow_obj.uuid_hex}` command "
                                f"to notify {ctx.author.mention} that you have sent the payment."
                            )

                    else:
                        embed = discord.Embed(title="Error!",
                                              description=f"You only have {comma_seperated_int(seller_tnbc_wallet.get_available_balance())} Leap Coin out of required {comma_seperated_int(escrow_obj.amount)} Leap Coin.\n\nPlease deposit extra {comma_seperated_int(escrow_obj.amount - seller_tnbc_wallet.get_available_balance())} Leap Coin using `/deposit tnbc` command.",
                                              color=0xe81111)
                else:
                    embed = discord.Embed(title="Error!", description=f"You cannot fund the escrow of status {escrow_obj.status}.", color=0xe81111)
            else:
                embed = discord.Embed(title="Error!", description="This escrow is funded when selling Leap Coin to the buy advertisement.", color=0xe81111)
        else:
            embed = discord.Embed(title="Error!", description="404 Not Found.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="escrow",
                            name="paid",
                            description="Mark the escrow as paid.",
                            options=[
                                create_option(
                                    name="escrow_id",
                                    description="Enter escrow id you want to fund.",
                                    option_type=3,
                                    required=True
                                )
                            ]
                            )
    async def escrow_paid(self, ctx, escrow_id: str):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)

        if Escrow.objects.filter(Q(successor=discord_user), Q(uuid_hex=escrow_id)).exists():

            escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

            conversation_channel = self.bot.get_channel(int(escrow_obj.conversation_channel_id))

            embed = discord.Embed(title="Escrow Marked Paid", description="Successfully notified the buyer.", color=0xe81111)

            if conversation_channel:
                seller = await self.bot.fetch_user(int(escrow_obj.initiator.discord_id))
                await conversation_channel.send(
                    f"{seller.mention}, {ctx.author.mention} has notified that they have sent the payment.\n\n"
                    f"Please use the command `/escrow release escrow_id: {escrow_obj.uuid_hex}` to release Leap Coin "
                    "**ONLY IF YOU HAVE RECEIVED THE PAYMENT (THIS ACTION CAN NOT BE REVERTED)**"
                )

        else:
            embed = discord.Embed(title="Error!", description="404 Not Found.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="escrow",
                            name="dispute",
                            description="Start an dispute.",
                            options=[
                                create_option(
                                    name="escrow_id",
                                    description="Enter escrow id you want to check the status of.",
                                    option_type=3,
                                    required=True
                                )
                            ]
                            )
    async def escrow_dispute(self, ctx, escrow_id: str):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)

        if Escrow.objects.filter(
            Q(initiator=discord_user) |
            Q(successor=discord_user),
            Q(uuid_hex=escrow_id)).exists():

            escrow_obj = await sync_to_async(Escrow.objects.get)(uuid_hex=escrow_id)

            if escrow_obj.status == Escrow.OPEN:
                escrow_obj.status = Escrow.DISPUTE
                escrow_obj.save()

                dispute = self.bot.get_channel(int(settings.DISPUTE_CHANNEL_ID))

                initiator = await self.bot.fetch_user(int(escrow_obj.initiator.discord_id))
                successor = await self.bot.fetch_user(int(escrow_obj.successor.discord_id))
                guild = self.bot.get_guild(int(settings.GUILD_ID))
                agent_role = discord.utils.get(guild.roles, id=int(settings.AGENT_ROLE_ID))

                user_profile = get_or_create_user_profile(discord_user)
                user_profile.total_disputes += 1
                user_profile.save()

                dispute_embed = discord.Embed(title="Dispute Alert!", description="", color=0xe81111)
                dispute_embed.add_field(name='Escrow ID', value=f"{escrow_obj.uuid_hex}", inline=False)
                dispute_embed.add_field(name='Amount', value=f"{convert_to_decimal(escrow_obj.amount)}")
                dispute_embed.add_field(name='Price (USDT)', value=convert_to_decimal(escrow_obj.price))
                dispute_embed.add_field(name='Seller', value=f"{initiator}")
                dispute_embed.add_field(name='Buyer', value=f"{successor}")
                dispute = await dispute.send(f"{agent_role.mention}", embed=dispute_embed)

                await dispute.add_reaction("👀")
                await dispute.add_reaction("✅")

                embed = discord.Embed(title="Escrow Disputed Successfully", description="", color=0xe81111)
                embed.add_field(name='Escrow ID', value=f"{escrow_obj.uuid_hex}", inline=False)
                embed.add_field(name='Amount', value=f"{comma_seperated_int(escrow_obj.amount)} Leap Coin")

                if escrow_obj.side == Escrow.BUY:
                    embed.add_field(name='Seller Pays', value=f"{comma_seperated_int(escrow_obj.amount + escrow_obj.fee)} Leap Coin")
                    embed.add_field(name='Buyer Receives', value=f"{comma_seperated_int(escrow_obj.amount)} Leap Coin")
                else:
                    embed.add_field(name='Fee', value=f"{comma_seperated_int(escrow_obj.fee)} Leap Coin")
                    embed.add_field(name='Buyer Receives', value=f"{comma_seperated_int(escrow_obj.amount - escrow_obj.fee)} Leap Coin")

                embed.add_field(name='Price (USDT)', value=convert_to_decimal(escrow_obj.price))
                embed.add_field(name='Seller', value=f"{initiator.mention}")
                embed.add_field(name='Buyer', value=f"{successor.mention}")
                embed.add_field(name='Status', value=f"{escrow_obj.status}")

                conversation_channel = self.bot.get_channel(int(escrow_obj.conversation_channel_id))
                if conversation_channel:
                    await conversation_channel.send(embed=embed)

            else:
                embed = discord.Embed(title="Error!", description=f"You cannot dispute the escrow of status {escrow_obj.status}.", color=0xe81111)

        else:
            embed = discord.Embed(title="Error!", description="404 Not Found.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="escrow", name="history", description="All your recent escrows.")
    async def escrow_history(self, ctx):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)

        if Escrow.objects.filter(Q(initiator=discord_user) | Q(successor=discord_user)).exists():
            escrows = (await sync_to_async(Escrow.objects.filter)(Q(initiator=discord_user) | Q(successor=discord_user))).order_by('-updated_at')[:8]

            embed = discord.Embed(color=0xe81111)

            for escrow in escrows:

                embed.add_field(name='Escrow ID', value=f"{escrow.uuid_hex}", inline=False)
                embed.add_field(name='Amount', value=f"{comma_seperated_int(escrow.amount)} Leap Coin")
                embed.add_field(name='Fee', value=f"{comma_seperated_int(escrow.fee)} Leap Coin")
                embed.add_field(name='Price (USDT)', value=convert_to_decimal(escrow.price))
                embed.add_field(name='Status', value=f"{escrow.status}")

        else:
            embed = discord.Embed(title="Oops..", description="You've not complete a single escrow.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)


def setup(bot):
    bot.add_cog(escrow(bot))
