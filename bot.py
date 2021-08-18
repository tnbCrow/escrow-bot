import os
import sys
import requests
import django
import humanize
import discord
from discord_slash import SlashCommand
from discord_slash.utils.manage_commands import create_option

# Django Setup on bot
sys.path.append(os.getcwd() + '/API')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()
from django.conf import settings
from escrow.models.user import User
from escrow.utils.scan_chain import match_transaction

# Environment Variables
TOKEN = os.environ.get('CROW_DISCORD_TOKEN')
TRADE_CHANNEL_ID = int(os.environ.get('TRADE_CHANNEL_ID'))
MANAGER_ID = int(os.environ.get('MANAGER_ID'))

# Initialize the Slash commands
client = discord.Client(intents=discord.Intents.all())
slash = SlashCommand(client, sync_commands=True)


@client.event
async def on_ready():
    print ("------------------------------------")
    print(f"tnbCrow Bot Running:")
    print ("------------------------------------")
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="TNBC grow"))


@slash.slash(name="rate", description="Last trade rate of TNBC.")
async def rate(ctx):
    # Gets the last trade rate through tnbcrow API
    r = requests.get('https://tnbcrow.pythonanywhere.com/statistics').json()

    # parse the rate to decimal since the rates are 10^4 of the actual rate
    last_rate = int(r["results"][0]["last_rate"]) / 10000

    embed = discord.Embed()
    embed.add_field(name = f"Last Trade Rate: ${last_rate}", value = "Use /trades to check recent verified trades!!")
    await ctx.send(embed=embed)


@slash.slash(name="trades", description="Recent trades!!")
async def trades(ctx):
    # gets the recent trades using the tnbcrow API
    r = requests.get('https://tnbcrow.pythonanywhere.com/recent-trades').json()
    trades = r["results"]
    cleaned_trades = []
    cleaned_trades.append("| Amount | Rate |")

    # create a list of trade post and append it to cleaned_trades list
    for trade in trades:
        data = f"| {trade['amount']} | ${trade['rate']/10000} |"
        cleaned_trades.append(data)

    # convert the list into string
    joined_string = "\n".join(cleaned_trades)
    
    await ctx.send(f"```{joined_string} ```", hidden=True)


@slash.slash(name="help", description="Crow Bot help!!")
async def help(ctx):
    embed=discord.Embed(title="Commands", color=discord.Color.blue())
    embed.add_field(name="/rate", value="Last verified trade of TNBC!!", inline=False)
    embed.add_field(name="/trades", value="Recent verified trades!!", inline=False)
    embed.add_field(name="/stats", value="TNBC Price Statistics!!", inline=False)
    await ctx.send(embed=embed, hidden=True)


@slash.slash(name="stats", description="TNBC Price Statistics!!")
async def stats(ctx):
    # get the total circulating supply through tnb-analytics github
    r1 = requests.get("https://raw.githubusercontent.com/itsnikhil/tnb-analysis/master/web/js/static.json").json()
    circulating_supply = r1["Total"]
    humanized_supply = humanize.intcomma(circulating_supply)

    # get the last trade rate using tnbcrow API
    r2 = requests.get('https://tnbcrow.pythonanywhere.com/statistics').json()
    last_rate = int(r2["results"][0]["last_rate"]) / 10000

    # calculate the market cap
    market_cap = int(circulating_supply * last_rate)
    humanized_cap = humanize.intcomma(market_cap)

    # create an embed and show it to users
    embed=discord.Embed(title="TNBC Price Statistics")
    embed.add_field(name="Circulating Supply", value=humanized_supply, inline=False)
    embed.add_field(name="Last Trade Rate", value=f"${last_rate}", inline=False)
    embed.add_field(name="Market Cap", value=f"${humanized_cap}", inline=False)
    await ctx.send(embed=embed)


@client.event
async def on_message(message):
    #ignore bot's own message
    if message.author.id == client.user.id:
        return

    # Delete old messages by the user in #trade channel
    if message.channel.id == TRADE_CHANNEL_ID:
        async for oldMessage in message.channel.history():
            if oldMessage.author == message.author and oldMessage.id != message.id:
                await oldMessage.delete()


@slash.slash(name="balance", description="Check User Balance!!")
async def balance(ctx):

    match_transaction()

    obj, created = User.objects.get_or_create(discord_id=ctx.author.id)

    embed = discord.Embed()
    embed.add_field(name='Withdrawl Address', value=obj.withdrawl_address, inline=False)
    embed.add_field(name='Balance', value=obj.balance)
    embed.add_field(name='Locked Amount', value=obj.locked)
    embed.add_field(name='Available Balance', value=obj.get_available_balance())

    await ctx.send(embed=embed, hidden=True)


@slash.slash(name="deposit", description="Check User Balance!!")
async def deposit(ctx):

    obj, created = User.objects.get_or_create(discord_id=ctx.author.id)

    embed = discord.Embed(title="Send TNBC to the address with memo!!")
    embed.add_field(name='Address', value=settings.ACCOUNT_NUMBER, inline=False)
    embed.add_field(name='MEMO', value=obj.memo, inline=False)
    embed.add_field(name="Sent?", value="Use /balance command to check the deposit!!")

    await ctx.send(embed=embed, hidden=True)


@slash.slash(name="setwithdrawladdress",
             description="Set new withdrawl address!!",
             options=[
                 create_option(
                    name="address",
                    description="Enter your withdrawl address.",
                    option_type=3,
                    required=True
                    )
                ])
async def set_withdrawl_address(ctx, address: str):

    obj, created = User.objects.get_or_create(discord_id=ctx.author.id)

    if len(address) == 64:
        obj.withdrawl_address = address
        obj.save()
        embed = discord.Embed()
        embed.add_field(name='Success!!', value=f"Successfully set {address} as your withdrawl address!!")

    else:
        embed = discord.Embed()
        embed.add_field(name='Error!!', value="Please enter a valid TNBC account number!!")

    await ctx.send(embed=embed, hidden=True)


@slash.slash(name="kill", description="Kill the bot!!")
async def kill(ctx):
    if int(ctx.author.id) == MANAGER_ID:
        print("Shutting Down the bot")
        await ctx.send("Bot shut Down", hidden=True)
        await client.close()
    else:
        print("nah")

client.run(TOKEN)
