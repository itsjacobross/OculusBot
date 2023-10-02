import discord

from discord.ext import commands
from discord import app_commands


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.disp = discord.Embed(title='Help Menu', color=discord.Colour.blurple())
        self.msg = None

    @app_commands.command(name='help')
    async def help(self, interaction, option: str = None):
        await self.cleanup()
#        self.disp.set_footer(text='Oculus Bot', icon_url='https://i.imgur.com/wRGYezp.png')
        self.disp.set_thumbnail(url='https://i.imgur.com/wRGYezp.png')
        option = option.lower() if option is not None else None
        if option == 'hangman':
            await self.hm(interaction)
        elif option == 'gamble':
            await self.gamb(interaction)
        elif option == 'blackjack':
            await self.bj(interaction)
        elif option == 'stats':
            await self.hmstats(interaction)
        elif option == 'channel':
            await self.privchan(interaction)
        elif option is None:
            await self.display(interaction)
        else:
            return

    async def hm(self, interaction):
        hm = '```-hangman, -hm```» Start a game of Hangman.'
        hm += '```-guess [letter], -g [letter]```» Guess a letter.'
        hm += '```-answer [word]```» Guess the entire word.'
        hm += '```-endhangman, -endhm```» End your game of Hangman early.'
        self.disp.add_field(name='**Playing Hangman**', value=hm, inline=False)
        self.disp.add_field(name='**Hangman Stats**', value='```-help Stats```» Commands used for Hangman stats.', inline=False)
        self.disp.add_field(name='**Private Hangman Channel**', value='```-help Channel```» Commands used for changing your private Hangman channel.', inline=False)
        self.msg = await interaction.response.send_message(embed=self.disp, ephemeral=True)

    async def hmstats(self, interaction):
        stats = '```-hmstats [user]```» Show Hangman stats for a user.'
        stats += '```-hmtop```» Show the top 3 Hangman players.'
        self.disp.add_field(name='**Hangman Stats**', value=stats, inline=False)
        self.msg = await interaction.send(embed=self.disp, ephemeral=True)

    async def privchan(self, interaction):
        chan = '```-add [user]```» Add a user to view your Hangman games.'
        chan += '```-remove [user]```» Remove a user from viewing your Hangman games.'
        chan += "```-leave```» Leave another user's private Hangman channel."
        self.disp.add_field(name='**Private Hangman Channel**', value=chan, inline=False)
        self.msg = await interaction.response.send_message(embed=self.disp, ephemeral=True)

    async def gamb(self, interaction):
        gamb = "```-money [user], -bal [user]```» Check a user's balance."
        gamb += "```-pay [amount] [user], -give [amount] [user]```» Send money to another user."
        gamb += "```-coinflip [amount], -flip [amount], -cf [amount]```» Double your money with a 50/50 chance."
        # gamb += "```-steal [amount] [user]```» Attempt to steal money from another user."
        gamb += "```-leaderboard, -ldb, -rank```» Show a leaderboard based on money."
        self.disp.add_field(name='**Gamble**', value=gamb, inline=False)
        self.msg = await interaction.response.send_message(embed=self.disp, ephemeral=True)

    async def bj(self, interaction):
        bj = "```-blackjack [amount], -bj [amount]```» Start a game of Blackjack."
        bj += "```-endblackjack, -endbj```» End your game of Blackjack early."
        self.disp.add_field(name='**Blackjack**', value=bj, inline=False)
        self.msg = await interaction.send(embed=self.disp, ephemeral=True)

    async def display(self, interaction):
        self.disp.add_field(name='**Hangman**', value='```-help Hangman```» Commands used for playing Hangman.', inline=False)
        self.disp.add_field(name='**Gamble**', value='```-help Gamble```» Commands used for almost everything gambling.', inline=False)
        self.disp.add_field(name='**Blackjack**', value="```-help Blackjack```» Commands used for playing Blackjack.", inline=False)
        self.disp.add_field(name='**Profile**', value="```-profile [user], -prof [user]```» Show a user's complete profile.", inline=False)
        self.msg = await interaction.response.send_message(embed=self.disp, ephemeral=True)

    async def cleanup(self):
        self.disp = discord.Embed(title='Help Menu', color=discord.Colour.blurple())
        self.msg = None


async def setup(bot):
    await bot.add_cog(Help(bot))
