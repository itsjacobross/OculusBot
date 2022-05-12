import discord

from discord.ext import commands


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.disp = discord.Embed(title='Help Menu', color=discord.Colour.blurple())
        self.msg = None

    @commands.command(name='help')
    async def help(self, ctx, option=None):
        await self.cleanup()
#        self.disp.set_footer(text='Oculus Bot', icon_url='https://i.imgur.com/wRGYezp.png')
        self.disp.set_thumbnail(url='https://i.imgur.com/wRGYezp.png')
        option = option.lower() if option is not None else None
        if option == 'hangman':
            await self.hm(ctx)
        elif option == 'gamble':
            await self.gamb(ctx)
        elif option == 'blackjack':
            await self.bj(ctx)
        elif option == 'stats':
            await self.hmstats(ctx)
        elif option == 'channel':
            await self.privchan(ctx)
        elif option is None:
            await self.display(ctx)
        else:
            return

    async def hm(self, ctx):
        hm = '```-hangman, -hm```» Start a game of Hangman.'
        hm += '```-guess [letter], -g [letter]```» Guess a letter.'
        hm += '```-answer [word]```» Guess the entire word.'
        hm += '```-endhangman, -endhm```» End your game of Hangman early.'
        self.disp.add_field(name='**Playing Hangman**', value=hm, inline=False)
        self.disp.add_field(name='**Hangman Stats**', value='```-help Stats```» Commands used for Hangman stats.', inline=False)
        self.disp.add_field(name='**Private Hangman Channel**', value='```-help Channel```» Commands used for changing your private Hangman channel.', inline=False)
        self.msg = await ctx.send(embed=self.disp)

    async def hmstats(self, ctx):
        stats = '```-hmstats [user]```» Show Hangman stats for a user.'
        stats += '```-hmtop```» Show the top 3 Hangman players.'
        self.disp.add_field(name='**Hangman Stats**', value=stats, inline=False)
        self.msg = await ctx.send(embed=self.disp)

    async def privchan(self, ctx):
        chan = '```-add [user]```» Add a user to view your Hangman games.'
        chan += '```-remove [user]```» Remove a user from viewing your Hangman games.'
        chan += "```-leave```» Leave another user's private Hangman channel."
        self.disp.add_field(name='**Private Hangman Channel**', value=chan, inline=False)
        self.msg = await ctx.send(embed=self.disp)

    async def gamb(self, ctx):
        gamb = "```-money [user], -bal [user]```» Check a user's balance."
        gamb += "```-pay [amount] [user], -give [amount] [user]```» Send money to another user."
        gamb += "```-coinflip [amount], -flip [amount], -cf [amount]```» Double your money with a 50/50 chance."
        # gamb += "```-steal [amount] [user]```» Attempt to steal money from another user."
        gamb += "```-leaderboard, -ldb, -rank```» Show a leaderboard based on money."
        self.disp.add_field(name='**Gamble**', value=gamb, inline=False)
        self.msg = await ctx.send(embed=self.disp)

    async def bj(self, ctx):
        bj = "```-blackjack [amount], -bj [amount]```» Start a game of Blackjack."
        bj += "```-endblackjack, -endbj```» End your game of Blackjack early."
        self.disp.add_field(name='**Blackjack**', value=bj, inline=False)
        self.msg = await ctx.send(embed=self.disp)

    async def display(self, ctx):
        self.disp.add_field(name='**Hangman**', value='```-help Hangman```» Commands used for playing Hangman.', inline=False)
        self.disp.add_field(name='**Gamble**', value='```-help Gamble```» Commands used for almost everything gambling.', inline=False)
        self.disp.add_field(name='**Blackjack**', value="```-help Blackjack```» Commands used for playing Blackjack.", inline=False)
        self.disp.add_field(name='**Profile**', value="```-profile [user], -prof [user]```» Show a user's complete profile.", inline=False)
        self.msg = await ctx.send(embed=self.disp)

    async def cleanup(self):
        self.disp = discord.Embed(title='Help Menu', color=discord.Colour.blurple())
        self.msg = None


def setup(bot):
    bot.add_cog(Help(bot))
