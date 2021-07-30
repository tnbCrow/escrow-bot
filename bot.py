import os
import humanize
import discord
from discord_slash import SlashCommand
import requests

TOKEN = os.environ.get('CROW_DISCORD_TOKEN')

client = discord.Client(intents=discord.Intents.all())
slash = SlashCommand(client, sync_commands=True)  # Declares slash commands through the client.

@client.event
async def on_ready():
    print ("------------------------------------")
    print(f"tnbCrow Bot Running:")
    print ("------------------------------------")
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="TNBC grow"))
    

@slash.slash(name="rate", description="Last trade rate of TNBC.")
async def rate(ctx):
    r = requests.get('https://tnbcrow.pythonanywhere.com/statistics').json()
    last_rate = int(r["results"][0]["last_rate"]) / 10000
    embed = discord.Embed()
    embed.add_field(name = f"Last Trade Rate: ${last_rate}", value = "Use /trades to check recent verified trades!!")
    await ctx.send(embed=embed)


@slash.slash(name="trades", description="Recent trades!!")
async def trades(ctx):
    r = requests.get('https://tnbcrow.pythonanywhere.com/recent-trades').json()
    trades = r["results"]
    cleaned_trades = []
    cleaned_trades.append("| Amount | Rate |")

    for trade in trades:
        data = f"| {trade['amount']} | ${trade['rate']/10000} |"
        cleaned_trades.append(data)
        
    joined_string = "\n".join(cleaned_trades)
    
    await ctx.send(f"```{joined_string} ```", hidden=True)


@slash.slash(name="help", description="Crow Bot help!!")
async def help(ctx):
    embed=discord.Embed(title="Commands", color=discord.Color.blue())
    embed.add_field(name="/rate", value="Last verified trade of TNBC!", inline=False)
    embed.add_field(name="/trades", value="Recent verified trades!", inline=False)
    await ctx.send(embed=embed, hidden=True)

@slash.slash(name="stats", description="TNBC Price Statistics!!")
async def stats(ctx):
    r1 = requests.get("https://raw.githubusercontent.com/itsnikhil/tnb-analysis/master/web/js/static.json").json()
    circulating_supply = r1["Total"]
    humanized_supply = humanize.intcomma(circulating_supply)
    
    r2 = requests.get('https://tnbcrow.pythonanywhere.com/statistics').json()
    last_rate = int(r2["results"][0]["last_rate"]) / 10000

    market_cap = int(circulating_supply * last_rate)
    humanized_cap = humanize.intcomma(market_cap)
    
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
    if message.channel.id == int(os.environ.get('TRADE_CHANNEL_ID')):
        async for oldMessage in message.channel.history():
            if oldMessage.author == message.author and oldMessage.id != message.id:
                await oldMessage.delete()
    
client.run(TOKEN)
