import discord
import random
import sqlite3 as sq

from discord.ext import commands, tasks


class Gamble(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.free_money.start()
        self.timer_check = False
        self.conn = sq.connect('database.db')
        self.c = self.conn.cursor()
        self.c.execute('''CREATE TABLE IF NOT EXISTS users
                       (user_id INTEGER, guild_id INTEGER,
                       money INTEGER, hmwins INTEGER, hmmoney INTEGER,
                       UNIQUE(user_id, guild_id))''')

    # Gives every user $15 every 30 minutes the bot is online.
    @tasks.loop(minutes=30.0)
    async def free_money(self):
        if self.timer_check:
            for guild in self.bot.guilds:
                for user in guild.members:
                    if not user.bot:
                        self.c.execute('''SELECT money
                                          FROM users
                                          WHERE (guild_id=? AND user_id=?)''',
                                       (int(guild.id), int(user.id)))
                        money = self.c.fetchone()[0]
                        self.c.execute('''UPDATE users
                                          SET money=?
                                          WHERE (guild_id=? AND user_id=?)''',
                                       (int(money) + 15, int(guild.id), int(user.id)))
                        self.conn.commit()
        else:
            self.timer_check = True

    @free_money.before_loop
    async def before_free_money(self):
        await self.bot.wait_until_ready()

    # Shows the requested user's balance.
    @commands.command(name='money', help="Check a user's current balance.",
                      aliases=['bal', 'balance'])
    async def money(self, ctx, user: discord.member.Member = None):
        if user is None:
            user = ctx.message.author
        if not user.bot:
            guildid = ctx.guild.id
            self.c.execute('''SELECT money
                              FROM users
                              WHERE (guild_id=? AND user_id=?)''',
                           (int(guildid), int(user.id)))
            balance = self.c.fetchone()[0]
            if user == ctx.message.author:
                await ctx.send("{}, your current balance is `${}`.".format(
                               user.name, balance))
            else:
                await ctx.send("{}'s current balance is `${}`."
                               .format(user.name, balance))
        else:
            await ctx.send("Bots don't have money!")

    @money.error
    async def money_error(self, ctx, error):
        print(error)
        await ctx.send('Format: -money [user]')

    # Give some money to another player.
    @commands.command(name='pay', help="Pay another user some money.",
                      aliases=['give'])
    async def pay(self, ctx, amount: int, user: discord.member.Member):
        if not user.bot:
            sender = ctx.message.author
            guildid = ctx.guild.id
            self.c.execute('''SELECT money
                              FROM users
                              WHERE (guild_id=? AND user_id=?)''',
                           (int(guildid), int(sender.id)))
            sender_balance = self.c.fetchone()[0]
            if user == sender:
                await ctx.send("You cannot send money to yourself.")
            elif int(amount) > int(sender_balance):
                await ctx.send("You are too poor. You only have `${}`."
                               .format(sender_balance))
            else:
                self.c.execute('''UPDATE users
                                  SET money=?
                                  WHERE (guild_id=? AND user_id=?)''',
                               (int(sender_balance) - int(amount), int(guildid), int(sender.id)))
                self.conn.commit()
                self.c.execute('''SELECT money
                                  FROM users
                                  WHERE (guild_id=? AND user_id=?)''',
                               (int(guildid), int(user.id)))
                user_balance = self.c.fetchone()[0]
                self.c.execute('''UPDATE users
                                  SET money=?
                                  WHERE (guild_id=? AND user_id=?)''',
                               (int(user_balance) + int(amount), int(guildid), int(user.id)))
                self.conn.commit()
                await ctx.send("You have paid `${}` to {}.".format(amount, user.name))
        else:
            await ctx.send("You cannot send money to a bot!")

    @pay.error
    async def pay_error(self, ctx, error):
        print(error)
        await ctx.send('Format: -pay [amount] [user]')

    # Gamble via 50/50 chances.
    @commands.command(name='coinflip', help="Bet money on a coin flip.",
                      aliases=['flip', 'cf'])
    async def flip(self, ctx, bet: str):
        user = ctx.message.author
        username = ctx.message.author.name
        guildid = ctx.guild.id
        self.c.execute('''SELECT money
                          FROM users
                          WHERE (guild_id=? AND user_id=?)''',
                       (int(guildid), int(user.id)))
        balance = self.c.fetchone()[0]
        if bet.lower() == 'all':
            bet = balance
        if int(bet) == 0:
            await ctx.send("Are you really trying to gamble with $0? Oh no...")
        elif int(bet) > int(balance):
            await ctx.send("{}, you are too poor. You only have `${}`."
                           .format(username, balance))
        else:
            win = random.randint(0, 1)
            if win == 0:
                self.c.execute('''UPDATE users
                                  SET money=?
                                  WHERE (guild_id=? AND user_id=?)''',
                               (int(balance) + int(bet), int(guildid), int(user.id)))
                self.conn.commit()
                await ctx.send("{}, you won! Your new balance is `${}`."
                               .format(username, int(balance) + int(bet)))
            else:
                self.c.execute('''UPDATE users
                                  SET money=?
                                  WHERE (guild_id=? AND user_id=?)''',
                               (int(balance) - int(bet), int(guildid), int(user.id)))
                self.conn.commit()
                await ctx.send("{}... you're a loser. Your new balance is `${}`."
                               .format(username, int(balance) - int(bet)))

    @flip.error
    async def flip_error(self, ctx, error):
        print(error)
        await ctx.send('Format: -flip [amount]')


def setup(bot):
    bot.add_cog(Gamble(bot))
