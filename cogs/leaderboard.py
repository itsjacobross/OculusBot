import discord
import sqlite3 as sq

from discord.ext import commands


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dict = {}
        self.conn = sq.connect('database.db')
        self.c = self.conn.cursor()

    @commands.command(name='leaderboard', help='Show a money leaderboard', aliases=['ldb'])
    async def leaderboard(self, ctx):
        guildid = ctx.guild.id
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
        await self.display(ctx)

    async def display(self, ctx):
        guildid = ctx.guild.id
        self.c.execute('''SELECT user_id, money
                          FROM users
                          WHERE guild_id=?
                          ORDER BY money DESC
                          LIMIT ? OFFSET ?''',
                       (int(guildid), self.dict[guildid]["size"], self.dict[guildid]["index"]))
        if self.dict[guildid]["msg"] is None:
            members = sum(not member.bot for member in ctx.message.guild.members)
            if members < self.dict[guildid]["size"]:
                self.dict[guildid]["size"] = members
            for num in range(self.dict[guildid]["size"]):
                money_values = self.c.fetchone()
                username = self.bot.get_user(int(money_values[0])).name
                bal = money_values[1]
                self.dict[guildid]["display"].add_field(name="Rank {}:".format(self.dict[guildid]["index"]+1), value="{}:\t\t${}\n".format(username, bal), inline=False)
                self.dict[guildid]["index"] += 1
            self.dict[guildid]["msg"] = await ctx.send(embed=self.dict[guildid]["display"])
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

    def cleanup(self, guildid):
        del self.dict[guildid]
        return

    @commands.command(name='rank', help='Show a money leaderboard', aliases=['myrank'])
    async def rank(self, ctx, user: discord.member.Member = None):
        user = ctx.message.author if user is None else user
        guildid = ctx.guild.id
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

        await ctx.send(f"{user.name} is ranked #{int(rank)+1} out of {len(my_db)} users with a balance of ${money_values[1]}.")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        guildid = reaction.message.guild.id
        self.c.execute('''SELECT *
                          FROM users
                          WHERE guild_id=?''',
                       (int(guildid),))
        my_db = self.c.fetchall()
        if reaction.message == self.dict[guildid]["msg"] and not user.bot:
            await reaction.remove(user)
            if not self.dict[guildid]["task"]:
                ctx = await self.bot.get_context(self.dict[guildid]["msg"])
                self.dict[guildid]["task"] = True
                if reaction.emoji == '⬅️':
                    if self.dict[guildid]["index"] < self.dict[guildid]["size"] * 2:
                        pass
                    else:
                        self.dict[guildid]["index"] -= self.dict[guildid]["size"] * 2
                        await self.display(ctx)
                elif reaction.emoji == '➡️':
                    if self.dict[guildid]["index"] + self.dict[guildid]["size"] > len(my_db):
                        pass
                    else:
                        await self.display(ctx)
                elif reaction.emoji == '🔄':
                    if self.dict[guildid]["index"] > 0:
                        self.dict[guildid]["index"] -= self.dict[guildid]["size"]
                    await self.display(ctx)
                elif reaction.emoji == '❌':
                    await self.dict[guildid]["msg"].delete()
                    self.cleanup(guildid)
                    return
                self.dict[guildid]["task"] = False


def setup(bot):
    bot.add_cog(Leaderboard(bot))
