from discord.ext import commands


class Special(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Kills the bot for fast restart.
    @commands.command(name='killbot', help='Kill the bot.', aliases=['kill'])
    @commands.is_owner()
    async def kill(self, ctx):
        await ctx.message.delete()
        print('Goodbye.')
        await self.bot.close()

    @kill.error
    async def kill_error(self, ctx, error):
        print(error)
        await ctx.send(error)


def setup(bot):
    bot.add_cog(Special(bot))
