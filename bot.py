import os
import discord
from discord_slash import SlashCommand
import requests

TOKEN = os.environ.get('CROW_DISCORD_TOKEN')

client = discord.Client(intents=discord.Intents.all())
slash = SlashCommand(client, sync_commands=True) # Declares slash commands through the client.

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
    
client.run(TOKEN)
