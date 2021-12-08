from discord.ext import commands
from discord_slash import cog_ext
import discord
import requests
import humanize
from datetime import datetime


class price(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    @cog_ext.cog_slash(name="rate", description="TNBC Price Statistics.")
    async def rate(self, ctx):

        await ctx.defer()

        # get the total circulating supply through tnb-analytics github
        r1 = requests.get("https://raw.githubusercontent.com/itsnikhil/tnb-analysis/master/web/js/static.json").json()
        circulating_supply = r1["Total"]
        humanized_supply = humanize.intcomma(circulating_supply)

        # get the last trade rate using tnbcrow API
        r2 = requests.get('https://tnbcrow.pythonanywhere.com/recent-trades').json()
        last_rate = int(r2["results"][0]["rate"]) / 10000

        # calculate the market cap
        market_cap = int(circulating_supply * last_rate)
        humanized_cap = humanize.intcomma(market_cap)

        # create an embed and show it to users
        embed = discord.Embed(color=0xe81111)
        embed.add_field(name="Last Trade Rate", value=f"{last_rate} USDC", inline=False)
        embed.add_field(name="Circulating Supply", value=humanized_supply, inline=False)
        embed.add_field(name="Market Cap", value=f"{humanized_cap} USDC", inline=False)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(price(bot))
