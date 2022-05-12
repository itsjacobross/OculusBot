import discord
import sqlite3 as sq

from discord.ext import commands


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.disp = discord.Embed(color=discord.Colour.red())
        self.user = None
        self.msg = None
        self.roles = []
        self.rolenames = None
        self.conn = sq.connect('database.db')
        self.c = self.conn.cursor()

    @commands.command(name='profile', aliases=['prof'])
    async def profile(self, ctx, user: discord.member.Member = None):
        await self.cleanup()
        self.user = ctx.message.author if user is None else user
        roles = self.user.roles[1:]
        if len(roles) > 1:
            roles.reverse()
            for role in roles:
                self.roles.append(role.name)
            self.rolenames = ''.join([let+', ' for let in self.roles])
            self.rolenames = self.rolenames[:-2]
        else:
            self.rolenames = "This user has no roles."
        await self.display(ctx) if not self.user.bot else await ctx.send("Bots are fake and don't have profiles.")

    async def display(self, ctx):
        guildid = ctx.guild.id
        self.disp.title = self.user.nick if self.user.nick is not None else self.user.name
        self.c.execute('''SELECT money, hmwins, hmmoney
                          FROM users
                          WHERE (guild_id=? AND user_id=?)''',
                       (int(guildid), int(self.user.id)))
        stats = self.c.fetchone()
        self.disp.add_field(name='Balance', value=f"${stats[0]}", inline=False)
        self.disp.add_field(name='Hangman Stats', value=f"Wins: {stats[1]}\nEarnings: ${stats[2]}", inline=False)
        self.disp.add_field(name='Roles', value=self.rolenames, inline=False)
        self.disp.set_footer(text='Oculus Bot', icon_url='https://i.imgur.com/VJ2brAT.png')
        self.disp.set_thumbnail(url=self.user.avatar_url)
        self.msg = await ctx.send(embed=self.disp)

    async def cleanup(self):
        self.user = None
        self.disp = discord.Embed(color=discord.Colour.red())
        self.msg = None
        self.roles = []
        self.rolesnames = None


def setup(bot):
    bot.add_cog(Profile(bot))
