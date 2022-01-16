import discord
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option, create_choice
from discord_slash.utils.manage_components import create_button, create_actionrow
from discord_slash.model import ButtonStyle
from django.conf import settings
from asgiref.sync import sync_to_async

from core.utils.shortcuts import convert_to_decimal, get_or_create_tnbc_wallet, get_or_create_discord_user, convert_to_int
from core.utils.logger import log_send

from escrow.models.advertisement import Advertisement
from escrow.models.escrow import Escrow
from escrow.utils import create_offer_table
from escrow.models.payment_method import PaymentMethod


class advertisement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_subcommand(base="adv",
                            name="create",
                            description="Create a new advertisement.",
                            options=[
                                create_option(
                                    name="order_type",
                                    description="Type of order you want to create.",
                                    option_type=3,
                                    required=True,
                                    choices=[
                                        create_choice(
                                            name="Buying",
                                            value="BUY"
                                        ),
                                        create_choice(
                                            name="Selling",
                                            value="SELL"
                                        )
                                    ]
                                ),
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
                                )
                            ]
                            )
    async def advertisement_create(self, ctx, order_type: str, amount_of_tnbc: int, price_per_tnbc: float):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)
        tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

        if PaymentMethod.objects.filter(user=discord_user).exists():

            if settings.MIN_TNBC_ALLOWED <= amount_of_tnbc <= 500000:

                if 0 < price_per_tnbc <= 100:

                    database_amount = amount_of_tnbc * settings.TNBC_MULTIPLICATION_FACTOR
                    price_in_integer = int(price_per_tnbc * settings.TNBC_MULTIPLICATION_FACTOR)

                    if order_type == Advertisement.SELL:

                        if convert_to_int(tnbc_wallet.get_available_balance()) >= amount_of_tnbc:

                            tnbc_wallet.locked += database_amount
                            tnbc_wallet.save()

                            advertisement, created = Advertisement.objects.get_or_create(owner=discord_user, price=price_in_integer, side=Advertisement.SELL, defaults={'amount': 0})
                            advertisement.amount += database_amount
                            advertisement.status = Advertisement.OPEN
                            advertisement.save()

                            sell_order_channel = self.bot.get_channel(int(settings.OFFER_CHANNEL_ID))
                            offer_table = create_offer_table(Advertisement.SELL, 20)

                            async for oldMessage in sell_order_channel.history():
                                await oldMessage.delete()

                            await sell_order_channel.send(f"**Sell Advertisements - Escrow Protected.**\n```{offer_table}```\nUse the command `/adv buy advertisement_id: ID amount: AMOUNT` to buy TNBC from the above advertisements.\nOr `/adv create` to create your own buy/ sell advertisement.")

                            await log_send(bot=self.bot, message=f"{ctx.author.mention} created SELL Advertisement.\nAmount: {amount_of_tnbc} TNBC.\nID: {advertisement.uuid_hex}")

                            embed = discord.Embed(title="Advertisement Created Successfully", description="", color=0xe81111)
                            embed.add_field(name='ID', value=f"{advertisement.uuid_hex}", inline=False)
                            embed.add_field(name='Amount', value=amount_of_tnbc)
                            embed.add_field(name='Price Per TNBC (USDT)', value=price_per_tnbc)
                            embed.set_footer(text="Use /adv my command list all your active advertisements.")

                        else:
                            embed = discord.Embed(title="Inadequate Funds!",
                                                  description=f"You only have {convert_to_int(tnbc_wallet.get_available_balance())} TNBC out of {amount_of_tnbc} TNBC available. \n Use `/deposit tnbc` to deposit TNBC!!",
                                                  color=0xe81111)
                    else:

                        advertisement, created = Advertisement.objects.get_or_create(owner=discord_user, price=price_in_integer, side=Advertisement.BUY, defaults={'amount': 0})
                        advertisement.amount += database_amount
                        advertisement.status = Advertisement.OPEN
                        advertisement.save()

                        buy_offer_channel = self.bot.get_channel(int(settings.TRADE_CHANNEL_ID))
                        offer_table = create_offer_table(Advertisement.BUY, 20)

                        async for oldMessage in buy_offer_channel.history():
                            await oldMessage.delete()
                        await buy_offer_channel.send(f"**Buy Advertisements.**```{offer_table}```\nUse the command `/adv sell advertisement_id: ID amount_of_tnbc: AMOUNT` to sell tnbc to above advertisement.\nOr `/adv create` command to create your own buy/ sell advertisements.")

                        await log_send(bot=self.bot, message=f"{ctx.author.mention} created BUY Advertisement.\nAmount: {amount_of_tnbc} TNBC.\nID: {advertisement.uuid_hex}.")

                        embed = discord.Embed(title="Yaay!",
                                              description="Buy order created successfully. Use the command `/adv cancel` to remove the advertisement.",
                                              color=0xe81111)
                else:
                    embed = discord.Embed(title="Error!",
                                          description="The price can not be less than 0.0 and more than 100.",
                                          color=0xe81111)
            else:
                embed = discord.Embed(title="Error!",
                                      description=f"You can not create an advertisement of less than {settings.MIN_TNBC_ALLOWED} TNBC and more than 500,000 TNBC.",
                                      color=0xe81111)
        else:
            embed = discord.Embed(title="No Payment Method Set.",
                                  description="Please use the command `/payment_method add` to add the payment method you'd like to receive money in.",
                                  color=0xe81111)
        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="adv",
                            name="my",
                            description="List all your advertisements.",
                            )
    async def advertisement_my(self, ctx):

        await ctx.defer(hidden=True)

        discord_user = get_or_create_discord_user(ctx.author.id)

        if Advertisement.objects.filter(status=Advertisement.OPEN, owner=discord_user).exists():

            advertisements = (await sync_to_async(Advertisement.objects.filter)(status=Advertisement.OPEN, owner=discord_user)).order_by('-updated_at')[:4]

            embed = discord.Embed(color=0xe81111)

            for advertisement in advertisements:
                embed.add_field(name='ID', value=f"{advertisement.uuid_hex}", inline=False)
                embed.add_field(name='Amount', value=convert_to_int(advertisement.amount))
                embed.add_field(name='Price Per TNBC (USDT)', value=convert_to_decimal(advertisement.price))
                embed.add_field(name='Side', value=advertisement.side)
            embed.set_footer(text="Use `/adv cancel` command cancel particular advertisement.")

        else:
            embed = discord.Embed(title="Oops..", description="You got no active advertisements.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="adv",
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
            advertisement.delete()

            if advertisement.side == Advertisement.BUY:

                buy_offer_channel = self.bot.get_channel(int(settings.TRADE_CHANNEL_ID))
                offer_table = create_offer_table(Advertisement.BUY, 20)

                async for oldMessage in buy_offer_channel.history():
                    await oldMessage.delete()

                await buy_offer_channel.send(f"**Buy Advertisements.**```{offer_table}```\nUse the command `/adv sell advertisement_id: ID amount_of_tnbc: AMOUNT` to sell tnbc to above advertisement.\nOr `/adv create` command to create your own buy/ sell advertisements.")

                await log_send(bot=self.bot, message=f"{ctx.author.mention} deleted BUY advertisement.\nAmount: {convert_to_int(advertisement.amount)} TNBC.")

            else:
                tnbc_wallet.locked -= advertisement.amount
                tnbc_wallet.save()

                sell_order_channel = self.bot.get_channel(int(settings.OFFER_CHANNEL_ID))
                offer_table = create_offer_table(Advertisement.SELL, 20)

                async for oldMessage in sell_order_channel.history():
                    await oldMessage.delete()

                await sell_order_channel.send(f"**Sell Advertisements - Escrow Protected.**\n```{offer_table}```\nUse the command `/adv buy advertisement_id: ID amount: AMOUNT` to buy TNBC from the above advertisements.\nOr `/adv create` to create your own buy/ sell advertisement.")

                await log_send(bot=self.bot, message=f"{ctx.author.mention} deleted SELL advertisement.\nAmount: {convert_to_int(advertisement.amount)} TNBC.")

            embed = discord.Embed(title="Advertisement Cancelled Successfully", description="", color=0xe81111)
            embed.set_footer(text="Use `/adv create` command create a new advertisement.")
        else:
            embed = discord.Embed(title="Error!", description="404 Not Found.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="adv",
                            name="buy",
                            description="Buy TNBC from the advertisement.",
                            options=[
                                create_option(
                                    name="advertisement_id",
                                    description="ID of the advertisement you want to buy from.",
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
    async def advertisement_buy(self, ctx, advertisement_id: str, amount_of_tnbc: int):

        await ctx.defer(hidden=True)

        buyer_discord_user = get_or_create_discord_user(ctx.author.id)

        if Advertisement.objects.filter(uuid_hex=advertisement_id, status=Advertisement.OPEN, side=Advertisement.SELL).exists():

            advertisement = await sync_to_async(Advertisement.objects.get)(uuid_hex=advertisement_id)

            if buyer_discord_user != advertisement.owner:

                if amount_of_tnbc >= settings.MIN_TNBC_ALLOWED:

                    database_amount = amount_of_tnbc * settings.TNBC_MULTIPLICATION_FACTOR

                    if advertisement.amount >= database_amount:
                        advertisement.amount -= database_amount
                        if advertisement.amount == 0:
                            advertisement.status = Advertisement.COMPLETED
                        advertisement.save()

                        guild = self.bot.get_guild(int(settings.GUILD_ID))
                        trade_chat_category = discord.utils.get(guild.categories, id=int(settings.TRADE_CHAT_CATEGORY_ID))

                        sell_order_channel = self.bot.get_channel(int(settings.OFFER_CHANNEL_ID))
                        offer_table = create_offer_table(Advertisement.SELL, 20)

                        async for oldMessage in sell_order_channel.history():
                            await oldMessage.delete()

                        await sell_order_channel.send(f"**Sell Advertisements - Escrow Protected.**\n```{offer_table}```\nUse the command `/adv buy advertisement_id: ID amount: AMOUNT` to buy TNBC from the above advertisements.\nOr `/adv create` to create your own buy/ sell advertisement.")

                        await log_send(bot=self.bot, message=f"{ctx.author.mention} is buying TNBC from the sell advertisement.\nAmount: {amount_of_tnbc} TNBC.\nID: {advertisement.uuid_hex}")

                        seller = await self.bot.fetch_user(int(advertisement.owner.discord_id))
                        agent_role = discord.utils.get(guild.roles, id=int(settings.AGENT_ROLE_ID))

                        overwrites = {
                            guild.default_role: discord.PermissionOverwrite(read_messages=False),
                            agent_role: discord.PermissionOverwrite(read_messages=True),
                            ctx.author: discord.PermissionOverwrite(read_messages=True),
                            seller: discord.PermissionOverwrite(read_messages=True)
                        }

                        trade_chat_channel = await guild.create_text_channel(f"{ctx.author.name}-{seller.name}", overwrites=overwrites, category=trade_chat_category)

                        integer_fee = amount_of_tnbc - int(amount_of_tnbc * (100 - settings.CROW_BOT_FEE) / 100)
                        database_fee = integer_fee * settings.TNBC_MULTIPLICATION_FACTOR

                        escrow_obj = await sync_to_async(Escrow.objects.create)(amount=database_amount,
                                                                                fee=database_fee,
                                                                                price=advertisement.price,
                                                                                initiator=advertisement.owner,
                                                                                successor=buyer_discord_user,
                                                                                side=Escrow.SELL,
                                                                                conversation_channel_id=trade_chat_channel.id,
                                                                                status=Escrow.OPEN)
                        embed = discord.Embed(title="Success.", description="", color=0xe81111)
                        embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
                        embed.add_field(name='Amount', value=amount_of_tnbc)
                        embed.add_field(name='Fee', value=integer_fee)
                        embed.add_field(name='Buyer Receives', value=f"{amount_of_tnbc - integer_fee}")
                        embed.add_field(name='Price (USDT)', value=convert_to_decimal(escrow_obj.price))
                        embed.add_field(name='Total (USDT)', value=convert_to_decimal(amount_of_tnbc * escrow_obj.price))
                        embed.set_footer(text="Use /escrow all command list all active escrows.")

                        payment_methods = PaymentMethod.objects.filter(user=advertisement.owner)

                        payment_method_message = ""

                        for payment_method in payment_methods:
                            payment_method_message += f"Payment Method: {payment_method.name}\nDetails: {payment_method.detail}\nConditions: {payment_method.condition}\n------\n"

                        await trade_chat_channel.send(f"{seller.mention}, {ctx.author.mention} is buying {amount_of_tnbc} TNBC at {convert_to_decimal(escrow_obj.price)}.\n{payment_method_message}", embed=embed)

                    else:
                        embed = discord.Embed(title="Error!", description=f"Advertisement only has {convert_to_int(advertisement.amount)} TNBC available to buy.", color=0xe81111)
                else:
                    embed = discord.Embed(title="Error!",
                                          description=f"You can not buy less than {settings.MIN_TNBC_ALLOWED} TNBC from an advertisement.",
                                          color=0xe81111)
            else:
                embed = discord.Embed(title="Error!", description="You can not buy TNBC from your own advertisement.", color=0xe81111)

        else:
            embed = discord.Embed(title="404!", description=f"Sell advertisement with id {advertisement_id} does not exist.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="adv",
                            name="sell",
                            description="Buy TNBC to the advertisement.",
                            options=[
                                create_option(
                                    name="advertisement_id",
                                    description="ID of the advertisement you want to sell.",
                                    option_type=3,
                                    required=True
                                ),
                                create_option(
                                    name="amount_of_tnbc",
                                    description="Amount of TNBC you'd like to sell.",
                                    option_type=4,
                                    required=True
                                )
                            ]
                            )
    async def advertisement_sell(self, ctx, advertisement_id: str, amount_of_tnbc: int):

        await ctx.defer(hidden=True)

        seller_discord_user = get_or_create_discord_user(ctx.author.id)
        seller_tnbc_wallet = get_or_create_tnbc_wallet(seller_discord_user)

        if Advertisement.objects.filter(uuid_hex=advertisement_id, status=Advertisement.OPEN, side=Advertisement.BUY).exists():

            advertisement = await sync_to_async(Advertisement.objects.get)(uuid_hex=advertisement_id)

            if seller_discord_user != advertisement.owner:

                if amount_of_tnbc >= settings.MIN_TNBC_ALLOWED:

                    database_amount = amount_of_tnbc * settings.TNBC_MULTIPLICATION_FACTOR
                    integer_fee = amount_of_tnbc - int(amount_of_tnbc * (100 - settings.CROW_BOT_FEE) / 100)
                    database_fee = integer_fee * settings.TNBC_MULTIPLICATION_FACTOR

                    fee_plus_amount = database_amount + database_fee

                    if seller_tnbc_wallet.get_available_balance() >= fee_plus_amount:

                        if advertisement.amount >= database_amount:
                            advertisement.amount -= database_amount
                            if advertisement.amount == 0:
                                advertisement.status = Advertisement.COMPLETED
                            advertisement.save()

                            guild = self.bot.get_guild(int(settings.GUILD_ID))
                            trade_chat_category = discord.utils.get(guild.categories, id=int(settings.TRADE_CHAT_CATEGORY_ID))

                            buy_offer_channel = self.bot.get_channel(int(settings.TRADE_CHANNEL_ID))
                            offer_table = create_offer_table(Advertisement.BUY, 20)

                            async for oldMessage in buy_offer_channel.history():
                                await oldMessage.delete()

                            await buy_offer_channel.send(f"**Buy Advertisements.**```{offer_table}```\nUse the command `/adv sell advertisement_id: ID amount_of_tnbc: AMOUNT` to sell tnbc to above advertisement.\nOr `/adv create` command to create your own buy/ sell advertisements.")

                            await log_send(bot=self.bot, message=f"{ctx.author.mention} is selling TNBC to the buy advertisement.\nAmount: {amount_of_tnbc} TNBC.\nID: {advertisement.uuid_hex}")

                            buyer = await self.bot.fetch_user(int(advertisement.owner.discord_id))
                            agent_role = discord.utils.get(guild.roles, id=int(settings.AGENT_ROLE_ID))

                            overwrites = {
                                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                agent_role: discord.PermissionOverwrite(read_messages=True),
                                ctx.author: discord.PermissionOverwrite(read_messages=True),
                                buyer: discord.PermissionOverwrite(read_messages=True)
                            }

                            trade_chat_channel = await guild.create_text_channel(f"{ctx.author.name}-{buyer.name}", overwrites=overwrites, category=trade_chat_category)

                            escrow_obj = await sync_to_async(Escrow.objects.create)(amount=database_amount,
                                                                                    fee=database_fee,
                                                                                    price=advertisement.price,
                                                                                    initiator=seller_discord_user,
                                                                                    successor=advertisement.owner,
                                                                                    side=Escrow.BUY,
                                                                                    conversation_channel_id=trade_chat_channel.id,
                                                                                    status=Escrow.OPEN)
                            seller_tnbc_wallet.locked += fee_plus_amount
                            seller_tnbc_wallet.save()

                            embed = discord.Embed(title="Success.", description="", color=0xe81111)
                            embed.add_field(name='ID', value=f"{escrow_obj.uuid_hex}", inline=False)
                            embed.add_field(name='Amount', value=amount_of_tnbc)
                            embed.add_field(name='Seller Pays', value=amount_of_tnbc + integer_fee)
                            embed.add_field(name='Buyer Receives', value=f"{amount_of_tnbc}")
                            embed.add_field(name='Price (USDT)', value=convert_to_decimal(escrow_obj.price))
                            embed.add_field(name='Total (USDT)', value=convert_to_decimal(amount_of_tnbc * escrow_obj.price))
                            embed.set_footer(text="Use /escrow all command list all active escrows.")

                            payment_methods = PaymentMethod.objects.filter(user=advertisement.owner)

                            payment_method_message = ""

                            for payment_method in payment_methods:
                                payment_method_message += f"Payment Method: {payment_method.name}\nDetails: {payment_method.detail}\nConditions: {payment_method.condition}\n------\n"

                            await trade_chat_channel.send(f"{buyer.mention}, {ctx.author.mention} is selling {amount_of_tnbc} TNBC at {convert_to_decimal(escrow_obj.price)}.\n{payment_method_message}", embed=embed)

                        else:
                            embed = discord.Embed(title="Error!", description=f"Advertisement only has {convert_to_int(advertisement.amount)} TNBC available to sell.", color=0xe81111)
                    else:
                        embed = discord.Embed(title="Error!",
                                              description=f"You only have {convert_to_int(seller_tnbc_wallet.get_available_balance())} TNBC out of required {convert_to_int(fee_plus_amount)} TNBC (including fees).",
                                              color=0xe81111)
                else:
                    embed = discord.Embed(title="Error!",
                                          description=f"You can not sell less than {settings.MIN_TNBC_ALLOWED} TNBC to an advertisement.",
                                          color=0xe81111)
            else:
                embed = discord.Embed(title="Error!", description="You can not sell TNBC to your own advertisement.", color=0xe81111)

        else:
            embed = discord.Embed(title="404!", description=f"Buy advertisement with id {advertisement_id} does not exist.", color=0xe81111)

        await ctx.send(embed=embed, hidden=True)


def setup(bot):
    bot.add_cog(advertisement(bot))
