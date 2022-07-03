import discord
from discord_slash import cog_ext
from discord.ext import commands


class guide(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_subcommand(base="guide",
                            name="seller",
                            description="Guide for sellers to trade on tnbcrow discord server.")
    async def guide_seller(self, ctx):

        await ctx.defer(hidden=True)

        embed = discord.Embed(title="Seller Guide | Crow Bot", description="", color=0xe81111)
        embed.add_field(name="Creating Sell Advertisement", value="------------------------------", inline=False)
        embed.add_field(name="1. Set your desired payment method", value="Use the command `/payment_method add` command to add payment method you'd like to receive the payment.", inline=False)
        embed.add_field(name="2. Create an advertisement", value="Create an advertisement using `/adv create` command.", inline=False)
        embed.add_field(name="3. Wait for the buyer", value="Once buyer buys from the advertisement, private channel is created within this server.", inline=False)
        embed.add_field(name="4. Deposit Leap Coin", value="Use the command `/deposit` to deposit tnbc into your crow bot account.", inline=False)
        embed.add_field(name="5. Fund the escrow", value="Use the command `/escrow fund escrow_id: ESCROW_ID` to fund Leap Coin to the escrow.", inline=False)
        embed.add_field(name="6. Wait for payment", value="Discuss the payment details in the private channel and wait for buyer to send the payment.", inline=False)
        embed.add_field(name="6. Release the escrow", value="Once you've received payment, use the command `/escrow release escrow_id: ESCROW_ID` to release Leap Coin into buyer's account.", inline=False)
        embed.add_field(name="Selling to buy advertisements", value="------------------------", inline=False)
        embed.add_field(name="1. Check the buy offers", value="Navigate to #buy-offers to check all buy offers.", inline=False)
        embed.add_field(name="2. Sell to the offer", value="Use the command `/adv sell advertisement_id: ID amount_of_tnbc: AMOUNT` to sell tnbc to the buy advertisement.", inline=False)
        embed.add_field(name="3. Discuss the payment details", value="Discuss the payment details in the private channel that was created and wait for the buyer to send the payment.", inline=False)
        embed.add_field(name="4. Release the escrow", value="Once you've received payment, use the command `/escrow release` to release Leap Coin into buyer's account.", inline=False)
        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_subcommand(base="guide",
                            name="buyer",
                            description="Guide for buyers to trade on tnbcrow discord server.")
    async def guide_buyer(self, ctx):

        await ctx.defer(hidden=True)
        embed = discord.Embed(title="Buyer Guide | Crow Bot", description="", color=0xe81111)
        embed.add_field(name="Buying from sell advertisements", value="------------------------", inline=False)
        embed.add_field(name="1. Check the available sell advertisements", value="Navigate to #sell-orders and check all available sell orders.", inline=False)
        embed.add_field(name="2. Buy from the advertisement", value="Use the command `/adv buy advertisement_id: ID` to buy tnbc from the advertisement. Private channel is created within the discord server.", inline=False)
        embed.add_field(name="3. Discuss the payment details", value="Discuss the payment details in the private channel.", inline=False)
        embed.add_field(name="4. Ask the seller to fund escrow", value="You'll be notified in private channel once the escrow is funded.", inline=False)
        embed.add_field(name="5. Send the payment", value="Send payment to the seller once the escrow is funded.", inline=False)
        embed.add_field(name="6. Wait for the seller to release escrow", value="Once the payment is received, the seller will release escrow.", inline=False)
        embed.add_field(name="7. Withdraw Leap Coin", value="Use the command `/withdraw` to withdraw Leap Coin into your wallet.", inline=False)
        embed.add_field(name="By creating buy advertisements", value="------------------------", inline=False)
        embed.add_field(name="1. Create buy advertisement", value="Use the command `/adv create side: Buying amount: AMOUNT price: PRICE`.", inline=False)
        embed.add_field(name="2. Wait for seller", value="Once the seller sells tnbc to the buy advertisement, a private channel is created within tnbcrow discord server.", inline=False)
        embed.add_field(name="3. Discuss the payment details", value="Discuss the payment details in the private channel.", inline=False)
        embed.add_field(name="4. Send the payment", value="Send agreed payment amount using the method.", inline=False)
        embed.add_field(name="5. Wait for the seller to release escrow", value="Once the payment is received, the seller will release escrow. You'll be notified in private channel about the status of the escrow.", inline=False)
        await ctx.send(embed=embed, hidden=True)


def setup(bot):
    bot.add_cog(guide(bot))
