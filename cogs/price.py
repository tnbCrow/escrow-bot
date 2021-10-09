from discord.ext import commands
from discord_slash import cog_ext
import discord
import requests
import humanize
from datetime import datetime

class price(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    @cog_ext.cog_slash(name="rate", description="Last trade rate of TNBC.")
    async def rate(self, ctx):

        await ctx.defer()

        # Gets the last trade rate through tnbcrow API
        r = requests.get('https://tnbcrow.pythonanywhere.com/statistics').json()

        # parse the rate to decimal since the rates are 10^4 of the actual rate
        last_rate = int(r["results"][0]["last_rate"]) / 10000

        embed = discord.Embed(color=0xe81111)
        embed.add_field(name=f"Last Trade Rate: ${last_rate}", value="Use /trades to check recent verified trades.")
        await ctx.send(embed=embed)

    @cog_ext.cog_slash(name="trades", description="Recent trades.")
    async def trades(self, ctx):

        await ctx.defer(hidden=True)

        # gets the recent trades using the tnbcrow API
        r = requests.get('https://tnbcrow.pythonanywhere.com/recent-trades').json()

        trades = r["results"]

        embed = discord.Embed(title="Recent verified trades.", color=0xe81111)

        for trade in trades:
            humanized_amount = humanize.intcomma(trade['amount'])
            transaction_time = datetime.strptime(trade['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
            humanized_date = humanize.naturaltime(transaction_time)
            embed.add_field(name="\u200b", value=f"{humanized_amount} TNBC at ${trade['rate']/10000} - {humanized_date}", inline=False)

        await ctx.send(embed=embed, hidden=True)

    
    @cog_ext.cog_slash(name="stats", description="TNBC Price Statistics.")
    async def stats(self, ctx):

        await ctx.defer()

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
        embed = discord.Embed(title="TNBC Price Statistics", color=0xe81111)
        embed.add_field(name="Circulating Supply", value=humanized_supply, inline=False)
        embed.add_field(name="Last Trade Rate", value=f"${last_rate}", inline=False)
        embed.add_field(name="Market Cap", value=f"${humanized_cap}", inline=False)
        await ctx.send(embed=embed)



def setup(bot):
    bot.add_cog(price(bot))
