import discord
import sqlite3 as sq

from discord.ext import commands
from discord import app_commands


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dict = {}
        self.conn = sq.connect('database.db')
        self.c = self.conn.cursor()

    @app_commands.command(name='leaderboard', description='Show a money leaderboard')
    async def leaderboard(self, interaction):
        guildid = interaction.guild.id
        if guildid in self.dict:
            await self.dict[guildid]["msg"].delete()
            self.cleanup(guildid)
        data = {"display": discord.Embed(title="Money Leaderboard"),
                "msg": None,
                "size": 10,
                "index": 0,
                "task": False
                }
        self.dict[guildid] = data
        self.dict[guildid]["display"].set_thumbnail(url='https://i.imgur.com/wRGYezp.png')
        await self.display(interaction)

    async def display(self, interaction):
        guildid = interaction.guild.id
        self.c.execute('''SELECT user_id, money
                          FROM users
                          WHERE guild_id=?
                          ORDER BY money DESC
                          LIMIT ? OFFSET ?''',
                       (int(guildid), self.dict[guildid]["size"], self.dict[guildid]["index"]))
        if self.dict[guildid]["msg"] is None:
            members = sum(not member.bot for member in interaction.guild.members)
            if members < self.dict[guildid]["size"]:
                self.dict[guildid]["size"] = members
            for num in range(self.dict[guildid]["size"]):
                money_values = self.c.fetchone()
                username = self.bot.get_user(int(money_values[0])).name
                bal = money_values[1]
                self.dict[guildid]["display"].add_field(name="Rank {}:".format(self.dict[guildid]["index"]+1), value="{}:\t\t${}\n".format(username, bal), inline=False)
                self.dict[guildid]["index"] += 1
            self.dict[guildid]["msg"] = await interaction.response.send_message(embed=self.dict[guildid]["display"])
            '''
            await self.dict[guildid]["msg"].add_reaction(emoji='⬅️')
            await self.dict[guildid]["msg"].add_reaction(emoji='➡️')
            await self.dict[guildid]["msg"].add_reaction(emoji='🔄')
            await self.dict[guildid]["msg"].add_reaction(emoji='❌')
        else:
            for num in range(self.dict[guildid]["size"]):
                money_values = self.c.fetchone()
                username = self.bot.get_user(int(money_values[0])).name
                bal = money_values[1]
                self.dict[guildid]["display"].set_field_at(index=num, name="Rank {}:".format(self.dict[guildid]["index"]+1), value="{}:\t\t${}\n".format(username, bal), inline=False)
                self.dict[guildid]["index"] += 1
            await self.dict[guildid]["msg"].edit(embed=self.dict[guildid]["display"])
            '''

    def cleanup(self, guildid):
        del self.dict[guildid]
        return

    @app_commands.command(name='rank', description='Show a money leaderboard')
    async def rank(self, interaction, user: discord.member.Member = None):
        user = interaction.user if user is None else user
        guildid = interaction.guild.id
        self.c.execute('''SELECT *
                          FROM users
                          WHERE guild_id=?''',
                       (int(guildid),))
        my_db = self.c.fetchall()
        self.c.execute('''SELECT user_id, money
                          FROM users
                          WHERE guild_id=?
                          ORDER BY money DESC''',
                       (int(guildid),))
        rank = 0
        for i in range(len(my_db)):
            money_values = self.c.fetchone()
            if int(money_values[0]) == user.id:
                break
            else:
                rank += 1

        await interaction.response.send_message(f"{user.name} is ranked #{int(rank)+1} out of {len(my_db)} users with a balance of ${money_values[1]}.")


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
