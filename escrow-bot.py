import os
import django
from discord_slash.context import ComponentContext
from discord.ext import commands
import discord
from discord_slash import SlashCommand
from discord_slash.utils.manage_components import create_button, create_actionrow
from discord_slash.model import ButtonStyle


# Django Setup on bot
DJANGO_DIRECTORY = os.getcwd()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.environ["DJANGO_SETTINGS_MODULE"])
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

from django.conf import settings
from core.utils.scan_chain import match_transaction, check_confirmation, scan_chain
from core.utils.shortcuts import convert_to_int, get_or_create_tnbc_wallet, get_or_create_discord_user

# Environment Variables
TOKEN = os.environ['CROW_DISCORD_TOKEN']

# Initialize the Slash commands
bot = commands.Bot(command_prefix=">")
slash = SlashCommand(bot, sync_commands=True)


@bot.event
async def on_ready():
    print("------------------------------------")
    print("tnbCrow Bot Running:")
    print("------------------------------------")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="/help"))

for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')


@slash.subcommand(base="help", name="general", description="List of Commands from General Category")
async def help_general(ctx):
    await ctx.defer(hidden=True)
    embed = discord.Embed(title="General Commands", color=0xe81111)
    embed.add_field(name="/balance", value="Check your crow bot balance.", inline=False)
    embed.add_field(name="/deposit tnbc", value="Deposit TNBC into your crow bot account.", inline=False)
    embed.add_field(name="/withdraw tnbc amount: AMOUNT", value="Withdraw TNBC into your TNBC wallet.", inline=False)
    embed.add_field(name="/set_withdrawl_address tnbc address: ADDRESS", value="Set a new TNBC withdrawal address.", inline=False)
    embed.add_field(name="/transactions tnbc", value="Check TNBC transaction history.", inline=False)
    embed.add_field(name="/profile user: USER", value="Check user's crow bot profile.", inline=False)
    embed.add_field(name="/payment_method add", value="Add a new payment method.", inline=False)
    embed.add_field(name="/payment_method all", value="List all your payment methods.", inline=False)
    embed.add_field(name="/payment_method remove", value="Delete particular payment method.", inline=False)
    embed.add_field(name="/rate", value="Check the last OTC trade rate of TNBC.")
    embed.add_field(name="/stats", value="Check TNBC price statistics.")
    embed.add_field(name="/guide buyer", value="Buyer guide for using crow bot.")
    embed.add_field(name="/guide seller", value="Seller guide for using crow bot.")
    embed.set_thumbnail(url=bot.user.avatar_url)
    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="help", name="advertisement", description="List of Commands related to advertisements.")
async def help_advertisement(ctx):
    await ctx.defer(hidden=True)
    embed = discord.Embed(title="Advertisement Related Commands", color=0xe81111)
    embed.add_field(name="/adv create amount: AMOUNT price: PRICE", value="Create a new advertisement.", inline=False)
    embed.add_field(name="/adv all", value="List all active advertisements.", inline=False)
    embed.add_field(name="/adv my", value="List all your active advertisements.", inline=False)
    embed.add_field(name="/adv cancel advertisement_id: ID", value="Cancel an active advertisement.", inline=False)
    embed.add_field(name="/adv status advertisement_id: ID", value="Check the status of the particular advertisement.", inline=False)
    embed.add_field(name="/adv buy advertisement_id: ID amount_of_tnbc: AMOUNT", value="Buy TNBC from the advertisement.", inline=False)
    embed.set_thumbnail(url=bot.user.avatar_url)
    await ctx.send(embed=embed, hidden=True)


@slash.subcommand(base="help", name="escrow", description="List of Commands related to escrows.")
async def help_escrow(ctx):
    embed = discord.Embed(title="Escrow Related Commands", color=0xe81111)
    embed.add_field(name="/escrow status escrow_id: ESCROW_ID", value="Check the status of a particular escrow.")
    embed.add_field(name="/escrow all", value="List all of your ongoing escrows.", inline=False)
    embed.add_field(name="/escrow release escrow_id: ESCROW_ID", value="Release TNBC to the buyer's account.", inline=False)
    embed.add_field(name="/escrow cancel escrow_id: ESCROW_ID", value="Cancel the particular escrow. Both buyer and seller needs to use the command for escrow cancellation.")
    embed.add_field(name="/escrow dispute escrow_id: ESCROW_ID", value="In the case of disagreement while trading, raise dispute and take the case to tnbcrow agent.", inline=False)
    embed.add_field(name="/escrow history escrow_id: ESCROW_ID", value="List all of your completed escrows.", inline=False)
    embed.set_thumbnail(url=bot.user.avatar_url)
    await ctx.send(embed=embed, hidden=True)


@bot.event
async def on_message(message):
    # ignore bot's own message
    if message.author.id == bot.user.id:
        return

    # Delete old messages by the user in #trade channel
    if message.channel.id == int(settings.TRADE_CHANNEL_ID):
        async for oldMessage in message.channel.history():
            if oldMessage.author == message.author and oldMessage.id != message.id:
                await oldMessage.delete()


@slash.component_callback()
async def chain_scan(ctx: ComponentContext):

    await ctx.defer(hidden=True)

    scan_chain()

    if os.environ['CHECK_TNBC_CONFIRMATION'] == 'True':

        check_confirmation()

    match_transaction()

    discord_user = get_or_create_discord_user(ctx.author.id)
    tnbc_wallet = get_or_create_tnbc_wallet(discord_user)

    embed = discord.Embed(title="Scan Completed", color=0xe81111)
    embed.add_field(name='New Balance', value=convert_to_int(tnbc_wallet.balance))
    embed.add_field(name='Locked Amount', value=convert_to_int(tnbc_wallet.locked))
    embed.add_field(name='Available Balance', value=convert_to_int(tnbc_wallet.get_available_balance()))
    embed.set_footer(text="Use /transactions tnbc command check your transaction history.")

    await ctx.send(embed=embed, hidden=True, components=[create_actionrow(create_button(custom_id="chain_scan", style=ButtonStyle.green, label="Check Again"))])


@slash.slash(name="kill", description="Kill the bot!")
async def kill(ctx):

    await ctx.defer(hidden=True)

    if int(ctx.author.id) == int(settings.BOT_MANAGER_ID):
        print("Shutting Down the bot")
        await ctx.send("Bot Shut Down", hidden=True)
        await bot.close()
    else:
        embed = discord.Embed(title="Nope", description="", color=0xe81111)
        embed.set_image(url="https://i.ibb.co/zQc3xDp/download-min-1.png")
        await ctx.send(embed=embed, hidden=True)

bot.run(TOKEN)
