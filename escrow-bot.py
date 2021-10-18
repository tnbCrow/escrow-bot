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
from escrow.models.trade_offers import TradeOffer
from core.utils.scan_chain import match_transaction, check_confirmation, scan_chain
from core.utils.shortcuts import get_or_create_tnbc_wallet, get_or_create_discord_user

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

@slash.slash(name="help", description="Crow Bot help.")
async def help(ctx):

    await ctx.defer(hidden=True)

    embed = discord.Embed(title="Getting Started", url="https://bot.tnbcrow.com/", description="Command List", color=0xe81111)
    embed.add_field(name="/balance", value="Check your crow bot balance.")
    embed.add_field(name="/deposit tnbc", value="Deposit TNBC into your crow bot account.")
    embed.add_field(name="/withdraw tnbc", value="Withdraw TNBC into your TNBC wallet.")
    embed.add_field(name="/escrow tnbc amount: AMOUNT user: USER", value="Create an escrow. Seller's fund will be locked once escrow is created.", inline=False)
    embed.add_field(name="/escrow status escrow_id: ESCROW_ID", value="Check the status of a particular escrow.")
    embed.add_field(name="/escrow all", value="List all of your ongoing escrows.", inline=False)
    embed.add_field(name="/escrow release escrow_id: ESCROW_ID", value="Release TNBC to the buyer's account.", inline=False)
    embed.add_field(name="/escrow cancel escrow_id: ESCROW_ID", value="Cancel the particular escrow. Both buyer and seller needs to use the command for escrow cancellation.")
    embed.add_field(name="/escrow dispute escrow_id: ESCROW_ID", value="In the case of disagreement while trading, raise dispute and take the case to tnbcrow agent.", inline=False)
    embed.add_field(name="/escrow history escrow_id: ESCROW_ID", value="List all of your completed escrows.", inline=False)
    embed.add_field(name="/rate", value="Check the last OTC trade rate of TNBC.")
    embed.add_field(name="/stats", value="Check TNBC price statistics.")
    embed.set_thumbnail(url=bot.user.avatar_url)

    await ctx.send(embed=embed, hidden=True)


@bot.event
async def on_message(message):
    # ignore bot's own message
    if message.author.id == bot.user.id:
        return

    discord_user = get_or_create_discord_user(message.author.id)

    # Delete old messages by the user in #trade channel
    if message.channel.id == int(settings.TRADE_CHANNEL_ID):
        async for oldMessage in message.channel.history():
            if oldMessage.author == message.author and oldMessage.id != message.id:
                TradeOffer.objects.filter(user=discord_user).delete()
                await oldMessage.delete()

        TradeOffer.objects.create(user=discord_user, message=message.content, discord_username=message.author)


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
    embed.add_field(name='New Balance', value=tnbc_wallet.get_int_balance())
    embed.add_field(name='Locked Amount', value=tnbc_wallet.get_int_locked())
    embed.add_field(name='Available Balance', value=tnbc_wallet.get_int_available_balance())

    await ctx.send(embed=embed, hidden=True, components=[create_actionrow(create_button(custom_id="chain_scan", style=ButtonStyle.green, label="Scan Again?"))])




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
