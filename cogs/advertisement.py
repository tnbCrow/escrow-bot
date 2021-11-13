import discord
import os
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option
from core.utils.shortcuts import convert_to_decimal, get_or_create_tnbc_wallet, get_or_create_discord_user, convert_to_int
from django.conf import settings
from asgiref.sync import sync_to_async
from escrow.models.advertisement import Advertisement
from escrow.models.escrow import Escrow
from escrow.utils import create_offer_table


class advertisement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_subcommand(base="advertisement",
                            name="create",
                            description="Create a new advertisement.",
                            options=[
                                create_option(
                                    name="amount_of_tnbc",
                                    description="Enter TNBC you want to put in for advertisement.",
                                    option_type=4,
                                    required=True
                                ),
                                create_option(
                                    name="price_per_tnbc",
                                    description="Rate you want to sell your TNBC at.",
                                    option_type=10,
                                    required=True
                                ),
                                create_option(
                                    name="payment_method",
                                    description="The payment methods you're accepting.",
                                    option_type=3,
                                    required=True
                                )
                            ]
                            )
    async def advertisement_create(self, ctx, amount_of_tnbc: int, price_per_tnbc: float, payment_method: str):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)
        tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

        if tnbc_wallet.get_int_available_balance() >= amount_of_tnbc:

            database_amount = amount_of_tnbc * settings.TNBC_MULTIPLICATION_FACTOR

            tnbc_wallet.locked += database_amount
            tnbc_wallet.save()

            price_in_integer = int(price_per_tnbc * settings.TNBC_MULTIPLICATION_FACTOR)
            advertisement = await sync_to_async(Advertisement.objects.create)(owner=discord_user, amount=database_amount, price=price_in_integer, payment_method=payment_method, status=Advertisement.OPEN)

            offer_channel = self.bot.get_channel(int(settings.OFFER_CHANNEL_ID))
            offer_table = create_offer_table(5)

            async for oldMessage in offer_channel.history():
                await oldMessage.delete()

            await offer_channel.send(f"Open Advertisements (Escrow Protected)```{offer_table}```")

            embed = discord.Embed(title="Advertisement Created Successfully", description="", color=0xe81111)
            embed.add_field(name='ID', value=f"{advertisement.uuid_hex}", inline=False)
            embed.add_field(name='Amount', value=amount_of_tnbc)
            embed.add_field(name='Price Per TNBC (USDT)', value=price_per_tnbc)
            embed.add_field(name='Payment Method', value=payment_method, inline=False)

        else:
            embed = discord.Embed(title="Inadequate Funds!",
                                  description=f"You only have {tnbc_wallet.get_int_available_balance()} TNBC out of {amount_of_tnbc} TNBC available. \n Use `/deposit tnbc` to deposit TNBC!!",
                                  color=0xe81111)
        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="offers",
                            name="all",
                            description="List all the active advertisements.",
                            )
    async def offers_all(self, ctx):

        await ctx.defer(hidden=True)

        offer_table = create_offer_table(5)

        await ctx.send(f"Open Advertisements (Escrow Protected)```{offer_table}```", hidden=True)

    @cog_ext.cog_subcommand(base="advertisement",
                            name="all",
                            description="List all your advertisements.",
                            )
    async def advertisement_all(self, ctx):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)

        if Advertisement.objects.filter(status=Advertisement.OPEN, owner=discord_user).exists():

            advertisements = (await sync_to_async(Advertisement.objects.filter)(status=Advertisement.OPEN, owner=discord_user))[:4]

            embed = discord.Embed(color=0xe81111)

            for advertisement in advertisements:
                embed.add_field(name='ID', value=f"{advertisement.uuid_hex}", inline=False)
                embed.add_field(name='Amount', value=convert_to_int(advertisement.amount))
                embed.add_field(name='Price Per TNBC (USDT)', value=convert_to_decimal(advertisement.price))
                embed.add_field(name='Payment Method', value=advertisement.payment_method, inline=False)

        else:
            embed = discord.Embed(title="Oops..", description="You got no active advertisements.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="advertisement",
                            name="status",
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
    async def advertisement_status(self, ctx, advertisement_id: str):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)

        if Advertisement.objects.filter(uuid_hex=advertisement_id, owner=discord_user, status=Advertisement.OPEN).exists():
            advertisement = await sync_to_async(Advertisement.objects.get)(uuid_hex=advertisement_id)

            embed = discord.Embed(color=0xe81111)
            embed.add_field(name='ID', value=f"{advertisement.uuid_hex}", inline=False)
            embed.add_field(name='Amount', value=convert_to_int(advertisement.amount))
            embed.add_field(name='Price Per TNBC (USDT)', value=convert_to_decimal(advertisement.price))
            embed.add_field(name='Payment Method', value=advertisement.payment_method, inline=False)

        else:
            embed = discord.Embed(title="Error!", description="404 Not Found.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="advertisement",
                            name="cancel",
                            description="Cancel the particular advertisement.",
                            options=[
                                create_option(
                                    name="advertisement_id",
                                    description="Enter the advertisement id you want to check the status of.",
                                    option_type=3,
                                    required=True
                                )
                            ]
                            )
    async def advertisement_cancel(self, ctx, advertisement_id: str):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)
        tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

        if Advertisement.objects.filter(uuid_hex=advertisement_id, owner=discord_user, status=Advertisement.OPEN).exists():

            advertisement = await sync_to_async(Advertisement.objects.get)(uuid_hex=advertisement_id)

            tnbc_wallet.locked -= advertisement.amount
            tnbc_wallet.save()

            advertisement.status = Advertisement.CANCELLED
            advertisement.save()

            offer_channel = self.bot.get_channel(int(settings.OFFER_CHANNEL_ID))
            offer_table = create_offer_table(5)

            async for oldMessage in offer_channel.history():
                await oldMessage.delete()

            await offer_channel.send(f"Open Advertisements (Escrow Protected)```{offer_table}```")

            embed = discord.Embed(title="Advertisement Cancelled Successfully", description="", color=0xe81111)
            embed.add_field(name='ID', value=f"{advertisement.uuid_hex}", inline=False)
            embed.add_field(name='Amount', value=convert_to_int(advertisement.amount))
            embed.add_field(name='Price Per TNBC (USDT)', value=convert_to_decimal(advertisement.price))
            embed.add_field(name='Payment Method', value=advertisement.payment_method)
            embed.add_field(name='Status', value=advertisement.status)

        else:
            embed = discord.Embed(title="Error!", description="404 Not Found.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="offers",
                            name="take",
                            description="Take the particular offer to initiate trade.",
                            options=[
                                create_option(
                                    name="offer_id",
                                    description="ID of the offer you want to claim.",
                                    option_type=3,
                                    required=True
                                ),
                                create_option(
                                    name="amount_of_tnbc",
                                    description="Amount of TNBC you'd like to buy.",
                                    option_type=4,
                                    required=True
                                )
                            ]
                            )
    async def offer_take(self, ctx, offer_id: str, amount_of_tnbc: int):

        await ctx.defer(hidden=True)

        buyer_discord_user = get_or_create_discord_user(ctx.author.id)

        if Advertisement.objects.filter(uuid_hex=offer_id, status=Advertisement.OPEN).exists():

            advertisement = await sync_to_async(Advertisement.objects.get)(uuid_hex=offer_id)

            if buyer_discord_user != advertisement.owner:
                database_amount = amount_of_tnbc * settings.TNBC_MULTIPLICATION_FACTOR

                if advertisement.amount >= database_amount:
                    advertisement.amount -= database_amount
                    if advertisement.amount == 0:
                        advertisement.status = Advertisement.COMPLETED
                    advertisement.save()

                    offer_channel = self.bot.get_channel(int(settings.OFFER_CHANNEL_ID))
                    offer_table = create_offer_table(5)

                    async for oldMessage in offer_channel.history():
                        await oldMessage.delete()

                    await offer_channel.send(f"Open Advertisements (Escrow Protected)```{offer_table}```")

                    trade_chat_category = discord.utils.get(ctx.guild.categories, id=int(settings.TRADE_CHAT_CATEGORY_ID))
                    agent_role = discord.utils.get(ctx.guild.roles, id=int(os.environ["AGENT_ROLE_ID"]))
                    seller = await self.bot.fetch_user(int(advertisement.owner.discord_id))

                    overwrites = {
                        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        agent_role: discord.PermissionOverwrite(read_messages=True),
                        ctx.author: discord.PermissionOverwrite(read_messages=True),
                        seller: discord.PermissionOverwrite(read_messages=True)
                    }

                    trade_chat_channel = await ctx.guild.create_text_channel(f"{ctx.author.name}-{seller.name}", overwrites=overwrites, category=trade_chat_category)

                    integer_fee = amount_of_tnbc - int(amount_of_tnbc * (100 - settings.CROW_BOT_FEE) / 100)
                    database_fee = integer_fee * settings.TNBC_MULTIPLICATION_FACTOR

                    escrow_obj = await sync_to_async(Escrow.objects.create)(amount=database_amount,
                                                                            fee=database_fee,
                                                                            price=advertisement.price,
                                                                            payment_method=advertisement.payment_method,
                                                                            initiator=advertisement.owner,
                                                                            successor=buyer_discord_user,
                                                                            status=Escrow.OPEN)
                    embed = discord.Embed(title="Success.", description="", color=0xe81111)
                    embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
                    embed.add_field(name='Amount', value=amount_of_tnbc)
                    embed.add_field(name='Fee', value=integer_fee)
                    embed.add_field(name='Price (USDT)', value=convert_to_decimal(escrow_obj.price))
                    embed.add_field(name='Total (USDT)', value=amount_of_tnbc * convert_to_decimal(escrow_obj.price))
                    embed.add_field(name='Payment Method', value=escrow_obj.payment_method)

                    await trade_chat_channel.send(f"{seller.mention}, {ctx.author.mention} is buying {amount_of_tnbc} TNBC at {convert_to_decimal(escrow_obj.price)}.\nPayment Method: {escrow_obj.payment_method}", embed=embed)

                else:
                    embed = discord.Embed(title="Error!", description="Advertisement does not have amount available to escrow.", color=0xe81111)

            else:
                embed = discord.Embed(title="Error!", description="You can not take your own advertisement.", color=0xe81111)

        else:
            embed = discord.Embed(title="Error!", description="404 Not Found.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)


def setup(bot):
    bot.add_cog(advertisement(bot))
