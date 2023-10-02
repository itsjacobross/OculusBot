import discord
import sqlite3 as sq

from discord.ext import commands
from discord import app_commands


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

    @app_commands.command(name='profile', description="Display a user's custom profile with stats")
    async def profile(self, interaction, user: discord.member.Member = None):
        await self.cleanup()
        self.user = interaction.user if user is None else user
        roles = self.user.roles[1:]
        if len(roles) > 1:
            roles.reverse()
            for role in roles:
                self.roles.append(role.name)
            self.rolenames = ''.join([let+', ' for let in self.roles])
            self.rolenames = self.rolenames[:-2]
        else:
            self.rolenames = "This user has no roles."
        await self.display(interaction) if not self.user.bot else await interaction.response.send_message("Bots are fake and don't have profiles.")

    async def display(self, interaction):
        guildid = interaction.guild.id
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
        self.disp.set_thumbnail(url=self.user.default_avatar)
        self.msg = await interaction.response.send_message(embed=self.disp)

    async def cleanup(self):
        self.user = None
        self.disp = discord.Embed(color=discord.Colour.red())
        self.msg = None
        self.roles = []
        self.rolesnames = None


async def setup(bot):
    await bot.add_cog(Profile(bot))
