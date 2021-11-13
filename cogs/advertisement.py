import discord
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option
from core.utils.shortcuts import convert_to_decimal, get_or_create_tnbc_wallet, get_or_create_discord_user, convert_to_int
from django.conf import settings
from asgiref.sync import sync_to_async
from table2ascii import table2ascii, PresetStyle
from escrow.models.advertisement import Advertisement
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

        await ctx.send(f"```{offer_table}```", hidden=True)


def setup(bot):
    bot.add_cog(advertisement(bot))
