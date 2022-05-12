import os
import random
import discord
import sqlite3 as sq
import math as m
import asyncio
import datetime

from dotenv import load_dotenv
from discord import Button, ButtonStyle
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions, MissingPermissions
from cogs.utils import checks

intents = discord.Intents.all()
intents.members = True

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

activity = discord.Game(name="-help")
bot = commands.Bot(command_prefix='-', activity=activity, status=discord.Status.dnd, intents=intents, case_insensitive=True)
bot.remove_command('help')

error_message = 'An unknown error occurred. Sorry!'

# --------------------------------------------------------------------------- #

# SQL FUNCTIONS

sql_create_stats_table = """ CREATE TABLE IF NOT EXISTS stats (
                                id integer PRIMARY KEY,
                                name integer NOT NULL,
                                money integer DEFAULT 1000,
                                hmwins integer DEFAULT 0,
                                hmmoney integer DEFAULT 0
                         );"""

sql_create_categories_table = """ CREATE TABLE IF NOT EXISTS cats (
                                     id integer PRIMARY KEY,
                                     guild_id integer NOT NULL,
                                     cst_id integer NOT NULL,
                                     hm_id integer NOT NULL
                              );"""


def check_for_db(guildid):
    if not os.path.exists("database.db"):
        os.mkdir(f"db/{guildid}")

    conn = create_connection(f"db/{guildid}/stats.db")
    if conn is not None:
        create_table(conn, sql_create_stats_table)

    conn = create_connection(f"db/{guildid}/cats.db")
    if conn is not None:
        create_table(conn, sql_create_categories_table)


def create_connection(db_file):
    conn = None
    try:
        conn = sq.connect(db_file)
        return conn
    except:
        pass

    return conn


def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except:
        pass


def create_stats(conn, stats):
    sql = """ INSERT INTO stats(name,money,hmwins,hmmoney)
              VALUES(?,?,?,?) """
    cur = conn.cursor()
    cur.execute(sql, stats)
    conn.commit()
    return cur.lastrowid


def create_cats(conn, cats):
    sql = """ INSERT INTO cats(guild_id,cst_id,hm_id)
              VALUES(?,?,?) """
    cur = conn.cursor()
    cur.execute(sql, cats)
    conn.commit()
    return cur.lastrowid


def fetch_data(conn, value, table, cond, condeq):
    query = f""" SELECT {value} FROM {table} WHERE {cond}={condeq}"""
    cur = conn.cursor()
    cur.execute(query)
    try:
        ret = cur.fetchone()[0]
    except:
        ret = None
    return ret


def user_exists(conn, user):
    index = fetch_data(conn, "id", "stats", "name", user.id)
    return index


def guild_exists(conn, guildid):
    index = fetch_data(conn, "id", "cats", "guildid", guildid)
    return index


def update_stats(conn, id, column, value):
    update = f"""UPDATE stats SET {column} = {value} WHERE id = {id}"""

    cur = conn.cursor()
    cur.execute(update)
    conn.commit()


def update_cats(conn, id, column, value):
    update = f"""UPDATE cats SET {column} = {value} WHERE id = {id}"""

    cur = conn.cursor()
    cur.execute(update)
    conn.commit()


# --------------------------------------------------------------------------- #

def bot_check(member):
    return member.bot


def find_user(user, guildid):
    check_for_db(guildid)
    conn = create_connection(f"db/{guildid}/stats.db")
    index = user_exists(conn, user)
    if index is None:
        index = create_stats(conn, (int(user.id), 1000, 0, 0))
    return index


def find_guild(guildid):
    check_for_db(guildid)
    conn = create_connection(f"db/{guildid}/cats.db")
    index = guild_exists(conn, guildid)
    if index is None:
        index = create_cats(conn, (int(guildid), 0, 0))
    return index


def alter(user, guildid, amount, column):
    check_for_db(guildid)
    conn = create_connection(f"db/{guildid}/stats.db")
    index = find_user(user, guildid)
    old = fetch_data(conn, column, "stats", "name", user.id)
    update_stats(conn, index, column, int(old) + int(amount))


def get_current(user, guildid, *argv):
    check_for_db(guildid)
    conn = create_connection(f"db/{guildid}/stats.db")
    values = []
    index = find_user(user, guildid)
    for arg in argv:
        values.append(fetch_data(conn, arg, "stats", "name", user.id))
    values.append(index)
    return values


class Gamble(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.free_money.start()
        self.timer_check = False

    # Gives every user $15 every 30 minutes the bot is online.
    @tasks.loop(minutes=30.0)
    async def free_money(self):
        if self.timer_check:
            for folder in os.listdir('db'):
                g = bot.get_guild(int(folder))
                guildid = int(folder)
                for user in g.members:
                    if not bot_check(user):
                        alter(user, guildid, 15, 'money')
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
        if not bot_check(user):
            guildid = ctx.message.guild.id
            balance = get_current(user, guildid, 'money')[0]
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
        if not bot_check(user):
            sender = ctx.message.author
            guildid = ctx.message.guild.id
            sender_balance = get_current(sender, guildid, 'money')[0]
            if user == sender:
                await ctx.send("You cannot send money to yourself.")
            elif amount > int(sender_balance):
                await ctx.send("You are too poor. You only have `${}`."
                               .format(sender_balance))
            else:
                alter(sender, guildid, -amount, 'money')
                alter(user, guildid, amount, 'money')
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
        guildid = ctx.message.guild.id
        balance = get_current(user, guildid, 'money')[0]
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
                alter(user, guildid, bet, 'money')
                new_bal = get_current(user, guildid, 'money')[0]
                await ctx.send("{}, you won! Your new balance is `${}`."
                               .format(username, new_bal))
            else:
                alter(user, guildid, -1 * int(bet), 'money')
                new_bal = get_current(user, guildid, 'money')[0]
                await ctx.send("{}... you're a loser. Your new balance is `${}`."
                               .format(username, new_bal))

    @flip.error
    async def flip_error(self, ctx, error):
        print(error)
        await ctx.send('Format: -flip [amount]')


# --------------------------------------------------------------------------- #

class Special(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Kills the bot for fast restart.
    @commands.command(name='killbot', help='Kill the bot.', aliases=['kill'])
    @has_permissions(administrator=True)
    async def kill(self, ctx):
        await ctx.message.delete()
        print('Goodbye.')
        await bot.close()

    @kill.error
    async def kill_error(self, ctx, error):
        print(error)
        await ctx.send(error)

    @commands.command(name='addstats')
    @has_permissions(administrator=True)
    async def addstats(self, ctx):
        guildid = ctx.message.guild.id
        check_for_db(guildid)
        conn = create_connection(f"db/{guildid}/stats.db")
        alter(ctx.message.author, guildid, 500, "money")
        await ctx.send(fetch_data(conn, "money", "stats", "name", ctx.message.author.id))


# --------------------------------------------------------------------------- #

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.disp = discord.Embed(title='Help Menu', color=discord.Colour.blurple())
        self.msg = None

    @commands.command(name='help')
    async def help(self, ctx, option=None):
        await self.cleanup()
        self.disp.set_footer(text='Oculus Bot', icon_url='https://i.imgur.com/VJ2brAT.png')
        self.disp.set_thumbnail(url='https://i.imgur.com/VJ2brAT.png')
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


# --------------------------------------------------------------------------- #

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.disp = discord.Embed(color=discord.Colour.red())
        self.user = None
        self.msg = None
        self.roles = []
        self.rolenames = None

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
        await self.display(ctx) if not bot_check(self.user) else await ctx.send("Bots are fake and don't have profiles.")

    async def display(self, ctx):
        guildid = ctx.message.guild.id
        self.disp.title = self.user.nick if self.user.nick is not None else self.user.name
        self.disp.add_field(name='Balance', value=f"${get_current(self.user, guildid, 'money')[0]}", inline=False)
        self.disp.add_field(name='Hangman Stats', value=f"Wins: {get_current(self.user, guildid, 'hmwins')[0]}\nEarnings: ${get_current(self.user, guildid, 'hmmoney')[0]}", inline=False)
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


# --------------------------------------------------------------------------- #

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.disp = discord.Embed(title="Money Leaderboard")
        self.msg = None
        self.active = False
        self.user = None
        self.index = 0
        self.task = False

    @commands.command(name='leaderboard', help='Show a money leaderboard', aliases=['rank', 'ranks', 'ldb'])
    async def leaderboard(self, ctx):
        if self.active:
            await self.msg.delete()
            self.cleanup()
        self.active = True
        self.user = ctx.message.author
        self.disp.set_thumbnail(url='https://i.imgur.com/VJ2brAT.png')
        await self.display(ctx)

    async def display(self, ctx):
        df = p.read_excel(spreadsheet)
        df = df.sort_values('money', ascending=False)
        guildid = ctx.message.guild.id
        counter = find_user(self.user, guildid)
        if self.msg is None:
            for num in range(10):
                username = df.iloc[self.index]['names']
                bal = df.iloc[self.index]['money']
                self.disp.add_field(name="Rank {}:".format(self.index+1), value="{}:\t\t${}\n".format(username, bal), inline=False)
                self.index += 1
            bal = get_current(self.user, guildid, 'money')[0]
            self.msg = await ctx.send("**`{}, you are currently ranked {}/{} with ${}.`**".format(self.user.name, counter+1, len(df), bal), embed=self.disp)
            await self.msg.add_reaction(emoji='⬅️')
            await self.msg.add_reaction(emoji='➡️')
            await self.msg.add_reaction(emoji='🔄')
            await self.msg.add_reaction(emoji='❌')
        else:
            for num in range(10):
                username = df.iloc[self.index]['names']
                bal = df.iloc[self.index]['money']
                self.disp.set_field_at(index=num, name="Rank {}:".format(self.index+1), value="{}:\t\t${}\n".format(username, bal), inline=False)
                self.index += 1
            bal = get_current(self.user, guildid, 'money')[0]
            await self.msg.edit(content="**`{}, you are currently ranked {}/{} with ${}.`**".format(self.user.name, counter+1, len(df), bal), embed=self.disp)

    def cleanup(self):
        self.disp = discord.Embed(title="Money Leaderboard")
        self.msg = None
        self.active = False
        self.index = 0
        self.user = None

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if reaction.message == self.msg and not bot_check(user):
            df = p.read_excel(spreadsheet)
            await reaction.remove(user)
            if not self.task:
                self.task = True
                self.user = user
                ctx = await self.bot.get_context(self.msg)
                if reaction.emoji == '⬅️':
                    if self.index < 20:
                        pass
                    else:
                        self.index -= 20
                        await self.display(ctx)
                elif reaction.emoji == '➡️':
                    if self.index + 10 > len(df):
                        pass
                    else:
                        await self.display(ctx)
                elif reaction.emoji == '🔄':
                    if self.index > 0:
                        self.index -= 10
                    await self.display(ctx)
                elif reaction.emoji == '❌':
                    await self.msg.delete()
                    self.cleanup()
                self.task = False


# --------------------------------------------------------------------------- #

class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.decks = 4 * 4
        self.cards = [self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks]
        self.deck = ["2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟", "🇯", "🇶", "🇰", "🇦"]
        self.cardsleft = sum(self.cards)
        self.dict = {}

    @commands.command(name='blackjack', help='Play a game of blackjack.',
                      aliases=['bj'])
    async def blackjack(self, ctx, buyin: str):
        if ctx.message.author.id not in self.dict:
            user = ctx.message.author
            data = {"display": discord.Embed(color=discord.Colour.blue()),
                    "msg": None,
                    "end": False,
                    "dealer_hand_real": '',
                    "dealer_hand": '❓',
                    "dealer_value": 0,
                    "dealer_aces": 0,
                    "player_hand": '',
                    "player_value": 0,
                    "player_aces": 0,
                    "prize": 0,
                    "buyin": 0
                    }
            self.dict[user.id] = data
            guildid = ctx.message.guild.id
            balance = get_current(user, guildid, 'money')[0]
            if buyin.lower() == 'all':
                buyin = balance
            if int(buyin) > int(balance):
                await ctx.send("You do not have that much money.")
            elif int(buyin) == 0:
                await ctx.send("You cannot play for $0.")
            else:
                alter(user, guildid, -1 * int(buyin), 'money')
                self.dict[user.id]["prize"] = int(buyin) * 2
                self.dict[user.id]["buyin"] = int(buyin)
                dealer_first = self.pick_rand()
                dealer_second = self.pick_rand()
                self.dict[user.id]["dealer_hand_real"] += dealer_first + ' ' + dealer_second
                self.dict[user.id]["dealer_hand"] += dealer_second
                self.dict[user.id]["dealer_value"] += self.get_value(dealer_first, None, user.id) + self.get_value(dealer_second, None, user.id)
                player_first = self.pick_rand()
                player_second = self.pick_rand()
                self.dict[user.id]["player_hand"] += player_first + ' ' + player_second
                self.dict[user.id]["player_value"] += self.get_value(player_first, user, user.id) + self.get_value(player_second, user, user.id)
                await self.display(ctx, user)
        else:
            await ctx.send('You are already playing a game of Blackjack!')

    async def display(self, ctx, user):
        player = f"**{user.name}'s Hand**"
        if self.dict[user.id]["end"]:
            dealer_hand = self.dict[user.id]["dealer_hand_real"]
        else:
            dealer_hand = self.dict[user.id]["dealer_hand"]
        print(f'Dealer = {self.dict[user.id]["dealer_value"]}, {user.name} = {self.dict[user.id]["player_value"]}')
        self.cardsleft = sum(self.cards)
        self.dict[user.id]["display"].title = 'BLACKJACK'
        self.dict[user.id]["display"].set_thumbnail(url=user.avatar_url)
        self.dict[user.id]["display"].set_footer(text=f'» Number of Decks: {int(self.decks/4)}\n» Cards Remaining: {self.cardsleft}\n» ${self.dict[user.id]["buyin"]} bet')
        if self.dict[user.id]["msg"] is None:
            self.dict[user.id]["display"].add_field(name="**Dealer's Hand**", value=f'> {dealer_hand}', inline=False)
            self.dict[user.id]["display"].add_field(name=player, value=f'> {self.dict[user.id]["player_hand"]}')
            self.dict[user.id]["msg"] = await ctx.send('Use the buttons to hit or stay.', embed=self.dict[user.id]["display"], components=[[
            Button(label="Hit",
                   custom_id="green",
                   style=ButtonStyle.green),
            Button(label="Stay",
                   custom_id="red",
                   style=ButtonStyle.red)]])
        else:
            self.dict[user.id]["display"].set_field_at(index=0, name="**Dealer's Hand**", value=f'> {dealer_hand}', inline=False)
            self.dict[user.id]["display"].set_field_at(index=1, name=player, value=f'> {self.dict[user.id]["player_hand"]}')
            await self.dict[user.id]["msg"].edit(embed=self.dict[user.id]["display"])
        if self.dict[user.id]["end"]:
            guildid = ctx.message.guild.id
            if self.dict[user.id]["dealer_value"] == self.dict[user.id]["player_value"] and self.dict[user.id]["dealer_value"] <= 21:
                alter(user, guildid, self.dict[user.id]["buyin"], 'money')
                bal = get_current(user, guildid, 'money')[0]
                msg = f'{user.name}, you tied with the dealer. Your original buy-in is returned to you. Your balance is `${bal}`.'
            elif (self.dict[user.id]["dealer_value"] <= 21 and (self.dict[user.id]["dealer_value"] >= self.dict[user.id]["player_value"] or self.dict[user.id]["player_value"] > 21)) or (self.dict[user.id]["dealer_value"] > 21 and self.dict[user.id]["player_value"] > 21):
                bal = get_current(user, guildid, 'money')[0]
                msg = f'Tough luck {user.name}, the dealer outplayed you. You now have `${bal}`.'
            else:
                alter(user, guildid, self.dict[user.id]["prize"], 'money')
                bal = get_current(user, guildid, 'money')[0]
                msg = f"Nice job on that W, {user.name}! You win `${self.dict[user.id]['prize']}`. Your new balance is `${bal}`."
            await ctx.send(msg)
            self.cleanup(user.id)
            return

        def check_button(i: discord.Interaction, button):
            return i.author == ctx.author and i.message == self.dict[user.id]["msg"]

        interaction, button = await bot.wait_for('button_click', check=check_button)
        if button.custom_id == "green" and interaction.author == user:
            msg = await interaction.respond(content=f"{user.name} hit.")
            await msg.delete()
            await self.hit(ctx, user, user.id)
            await self.display(ctx, user)
        elif button.custom_id == "red" and interaction.author == user:
            msg = await interaction.respond(content=f"{user.name} decided to stay.")
            await msg.delete()
            await self.hit(ctx, None, user.id)
            await self.display(ctx, user)

# LIST INDEX OUT OF RANGE OCCURS WHEN:
# PLAYER 1 STARTS GAME
# PLAYER 2 STARTS GAME
# PLAYER 1 FINISHES GAME
# PLAYER 1 STARTS GAME

    @commands.command(name='endblackjack', aliases=['endbj', 'bjend', 'blackjackend'])
    async def endbj(self, ctx):
        if ctx.message.author.id in self.dict:
            guildid = ctx.message.guild.id
            alter(ctx.message.author, guildid, self.dict[ctx.message.author.id]["buyin"], 'money')
            await ctx.send(f'You have decided to fold.')
            self.cleanup(ctx.message.author.id)
        else:
            await ctx.send('You do not have an active game of Blackjack.')

    def pick_rand(self):
        self.resetdeck() if self.cardsleft < 4 else None
        index = random.choice(range(0, len(self.deck)))
        choice = self.deck[index] if self.cards[index] != 0 else self.pick_rand()
        self.cards[index] -= 1 if self.cards[index] != 0 else 0
        return choice

    def cleanup(self, id):
        del self.dict[id]
        return

    def resetdeck(self):
        self.decks = 4 * 4
        for x in range(len(self.cards)):
            self.cards[x] = self.decks
        self.cardsleft = sum(self.cards)
        return

    def get_value(self, string, player, id):
        try:
            value = int(string[0])
        except:
            if string[0] == '🇦':
                value = 11
                if player is None:
                    self.dict[id]["dealer_aces"] += 1
                else:
                    self.dict[id]["player_aces"] += 1
            else:
                value = 10
        return int(value)

    async def hit(self, ctx, player, id):
        if player is not None:
            new_card = self.pick_rand()
            self.dict[id]["player_hand"] += ' ' + new_card
            self.dict[id]["player_value"] += self.get_value(new_card, player, id)
            if self.dict[id]["player_value"] > 21 and self.dict[id]["player_aces"] > 0:
                self.dict[id]["player_aces"] -= 1
                self.dict[id]["player_value"] -= 10
            elif self.dict[id]["player_value"] > 21:
                await self.hit(ctx, None, id)
        else:
            if self.dict[id]["dealer_hand_real"] == '🇦 🇦':
                self.dict[id]["dealer_aces"] -= 1
                self.dict[id]["dealer_value"] -= 10
            while(self.dict[id]["dealer_value"] < 17):
                new_card = self.pick_rand()
                self.dict[id]["dealer_hand"] += ' ' + new_card
                self.dict[id]["dealer_hand_real"] += ' ' + new_card
                self.dict[id]["dealer_value"] += self.get_value(new_card, None, id)
                if self.dict[id]["dealer_value"] > 21 and self.dict[id]["dealer_aces"] > 0:
                    self.dict[id]["dealer_aces"] -= 1
                    self.dict[id]["dealer_value"] -= 10
            self.dict[id]["end"] = True


# --------------------------------------------------------------------------- #

class Hangman(commands.Cog):
    def __init__(self, bot, path_to_dict):
        self.bot = bot
        self.player = []
        self.word = []
        f = open(path_to_dict, 'r')
        self.dict = f.readlines()
        f.close()
        self.stage = []
        self.guessed = []
        self.real_word = []
        self.wrong = []
        self.category = None
        self.channel = []
        self.disp = []
        self.msg = []
        self.authormsg = None
        self.botmsg = None
        self.win = []
        self.prize = []
        self.active = 0
        self.set = []
        self.hmtop = discord.Embed(title="Hangman Top Stats", color=discord.Colour.darker_grey())
        self.topmsg = None
        self.images = [['https://i.imgur.com/bD68c54.png', 'https://i.imgur.com/Bi1S1r2.png', 'https://i.imgur.com/DKeCsD3.png', 'https://i.imgur.com/aSMmgDH.png', 'https://i.imgur.com/3pPsgr7.png', 'https://i.imgur.com/BCb26Ne.png'],
                       ['https://i.imgur.com/bD68c54.png', 'https://i.imgur.com/Bi1S1r2.png', 'https://i.imgur.com/DKeCsD3.png', 'https://i.imgur.com/aSMmgDH.png', 'https://i.imgur.com/3pPsgr7.png', 'https://i.imgur.com/BCb26Ne.png']]
        self.check_hangman_activity.start()
        self.timer_check = False

    # Gives every user $5 every 10 minutes the bot is online.
    @tasks.loop(minutes=30.0)
    async def check_hangman_activity(self):
        if self.timer_check:
            for text_channel in self.bot.get_channel(854455329503838258).text_channels:
                messages = await text_channel.history(after=(datetime.datetime.now() - datetime.timedelta())).flatten()
                if len(messages) == 0:
                    await text_channel.delete()
        else:
            self.timer_check = True

    @commands.command(name='hangman', help='Start a game of hangman.',
                      aliases=['hm'])
    async def hm(self, ctx):
        if ctx.message.author not in self.player:
#            if self.active > 0:
#                await asyncio.sleep(self.active*1.5)
#            self.active += 1
            index = len(self.player)
            self.player.append(ctx.message.author)
            self.word.append(random.choice(self.dict).rstrip())
            self.stage.append(0)
            self.guessed.append(set())
            print(f"{ctx.message.author.name}'s Hangman word: {self.word[index]}")
            self.real_word.append(['_' for i in range(len(self.word[index]))])
            self.wrong.append([])
            self.category = self.bot.get_channel(854455329503838258) if self.category is None else self.category
            self.disp.append(discord.Embed(color=discord.Colour.darker_grey()))
            self.win.append(False)
            self.prize.append(2000)
            self.set.append(random.choice(range(len(self.images))) - 1)
            self.msg.append(None)
            text_channel_list = []
            for channel in self.category.text_channels:
                text_channel_list.append(channel.name)
            player_channel = 'hangman-' + self.player[index].name.lower()
            if player_channel not in text_channel_list:
                new_chan = await self.category.create_text_channel(player_channel)
                self.channel.append(new_chan)
                await new_chan.edit(topic=('See additional hangman commands with -help hangman'))
            else:
                self.channel.append(discord.utils.get(ctx.guild.channels, name=player_channel))
            await self.channel[index].set_permissions(self.player[index], view_channel=True, send_messages=True)
            await ctx.send(f'Starting your game of Hangman in <#{self.channel[index].id}>')
            await self.display(self.channel[index], index)
        else:
            await self.clear_msg()
            self.authormsg = ctx.message
            self.botmsg = await ctx.send('You already have an active game of Hangman!')

    @commands.command(name='hmstats')
    async def hmstats(self, ctx, user: discord.member.Member = None):
        user = ctx.message.author if user is None else user
        if not bot_check(user):
            guildid = ctx.message.guild.id
            values = get_current(user, guildid, 'hmwins', 'hmmoney')
            x = 'win' if int(values[0]) == 1 else 'wins'
            if user == ctx.message.author:
                msg = "{}, you currently have `{}` {} and `${}` total earnings.".format(user.name, values[0], x, values[1])
            else:
                msg = "{} currently has `{}` {} and `${}` total earnings.".format(user.name, values[0], x, values[1])
            await ctx.send(msg)
        else:
            await ctx.send("Bots don't play hangman lol!")

    @commands.command(name='hmtop')
    async def hmtop(self, ctx):
        await self.cleanuptop()
        df = p.read_excel(spreadsheet)
        dfwin = df.sort_values('hmwins', ascending=False)
        dfmoney = df.sort_values('hmmoney', ascending=False)
        wins_msg, money_msg = '```', '```'
        for num in range(3):
            win_user = dfwin.iloc[num]['names']
            money_user = dfmoney.iloc[num]['names']
            wins = dfwin.iloc[num]['hmwins']
            money = dfmoney.iloc[num]['hmmoney']
            wins_msg += f"#{num+1} » {win_user} » {wins}\n"
            money_msg += f"#{num+1} » {money_user} » ${money}\n"
        wins_msg += '```'
        money_msg += '```'
        self.hmtop.add_field(name="Total Wins", value=wins_msg, inline=False)
        self.hmtop.add_field(name="Total Earnings", value=money_msg, inline=False)
        self.hmtop.set_thumbnail(url='https://i.imgur.com/VJ2brAT.png')
        self.topmsg = await ctx.send(embed=self.hmtop)

    async def cleanuptop(self):
        self.hmtop = discord.Embed(title="Hangman Top Stats", color=discord.Colour.darker_grey())
        self.topmsg = None

    @commands.command(name='guess', help='Guess a letter.',
                      aliases=['g'])
    async def guess(self, ctx, letter: str):
#        if self.active > 0:
#            await asyncio.sleep(self.active*1.5)
        letter = letter.lower()
        index = self.player.index(ctx.message.author)
        if self.player[index] == ctx.message.author and ctx.message.channel == self.channel[index]:
#            self.active += 1
            await self.clear_msg()
            self.authormsg = ctx.message
            if len(letter) > 1:
                self.botmsg = await ctx.send('Your guess must be 1 character!')
            elif letter not in self.guessed[index]:
                self.guessed[index].add(letter)
                if letter in self.word[index]:
                    self.botmsg = await ctx.send('Good guess!')
                    for i in range(len(self.word[index])):
                        if self.word[index][i:i+1] == letter:
                            self.real_word[index][i] = letter
                else:
                    self.botmsg = await ctx.send('Bad guess...')
                    self.stage[index] += 1
                    self.wrong[index].append(letter)
            else:
                self.botmsg = await ctx.send('You have already guessed that!')
            potential_win = ''.join(self.real_word[index])
            if potential_win == self.word[index]:
                self.win[index] = True
            await self.display(ctx, index)

    @guess.error
    async def guess_error(self, ctx, error):
        self.authormsg = ctx.message
        self.botmsg = await ctx.send('Format: -guess [letter]')
        print(error)

    @commands.command(name='answer', help='Guess the word.')
    async def answer(self, ctx, word: str):
#        if self.active > 0:
#            await asyncio.sleep(self.active*1.5)
        word = word.lower()
        index = self.player.index(ctx.message.author)
        if self.player[index] == ctx.message.author and ctx.message.channel == self.channel[index]:
#            self.active += 1
            await self.clear_msg()
            self.authormsg = ctx.message
            if word == self.word[index]:
                self.botmsg = await ctx.send('NICE!')
                self.win[index] = True
            else:
                self.botmsg = await ctx.send('Bad guess...')
                self.stage[index] += 1
            await self.display(ctx, index)

    @answer.error
    async def answer_error(self, ctx, error):
        self.authormsg = ctx.message
        self.botmsg = await ctx.send('Format: -answer [word]')
        print(error)

    @commands.command(name='endhm', help='End the current game.', aliases=['hmend', 'endhangman', 'hangmanend'])
    async def endhm(self, ctx):
        await self.clear_msg()
        if ctx.message.author in self.player:
            index = self.player.index(ctx.message.author)
            await ctx.send(f'You have decided to end the game early. The word was: {self.word[index]}.')
            self.cleanup(index)
        else:
            await ctx.send('A game is not currently in progress.')

    async def clear_msg(self):
        if self.authormsg or self.botmsg is not None:
            try:
                await self.authormsg.delete()
            except:
                pass
            try:
                await self.botmsg.delete()
            except:
                pass

    def cleanup(self, index):
        del self.word[index]
        del self.stage[index]
        del self.guessed[index]
        del self.real_word[index]
        del self.wrong[index]
        del self.channel[index]
        del self.msg[index]
        self.authormsg = None
        self.botmsg = None
        del self.player[index]
        del self.disp[index]
        del self.win[index]
        del self.prize[index]
        del self.set[index]
        return

    async def display(self, ctx, index):
        wrd = '``` ' + ''.join([let+' ' for let in self.word[index]]) + '```' if self.win[index] else '``` ' + ''.join([let+' ' for let in self.real_word[index]]) + '```'
        guessed = ''.join([let+' ' for let in self.guessed[index]])
        self.stage[index] = len(self.images[self.set[index]]) - 1 if self.win[index] else self.stage[index]
        self.disp[index].title = 'HANGMAN'
        self.disp[index].description = wrd
        self.disp[index].set_thumbnail(url=self.player[index].avatar_url)
        self.disp[index].set_image(url=self.images[self.set[index]][self.stage[index]])
        self.disp[index].set_footer(text=f'» Letters guessed: {guessed}')
        if self.msg[index] is None:
            self.msg[index] = await ctx.send('Use `-guess <letter>` or `-answer <word>` to guess.', embed=self.disp[index])
        else:
            await self.msg[index].edit(embed=self.disp[index])
        if self.win[index]:
            if len(self.wrong[index]) > 0:
                self.prize[index] -= m.floor(self.prize[index] * float(len(self.wrong[index])/10))
            await self.clear_msg()
            guildid = ctx.message.guild.id
            alter(self.player[index], guildid, self.prize[index], 'money')
            alter(self.player[index], guildid, 1, 'hmwins')
            alter(self.player[index], guildid, self.prize[index], 'hmmoney')
            bal = get_current(self.player[index], guildid, 'money')[0]
            await ctx.send(f"Congratulations {self.player[index].name}, you guessed the word and earned `${self.prize[index]}`! You now have `${bal}`.")
            self.cleanup(index)
            return
        if self.stage[index] == len(self.images[self.set[index]]) - 1:
            await self.clear_msg()
            await ctx.send(f"{self.player[index].name}... you lost! The word was: `{self.word[index]}`")
            self.cleanup(index)
#        self.active -= 1

    @commands.command(name='add')
    async def add(self, ctx, user: discord.member.Member):
        self.category = self.bot.get_channel(854455329503838258) if self.category is None else self.category
        channel_names = [channel.name for channel in self.category.text_channels]
        player_channel = 'hangman-' + ctx.message.author.name.lower()
        if user != ctx.message.author and player_channel in channel_names:
            channel = discord.utils.get(ctx.guild.channels, name=player_channel)
            await channel.set_permissions(user, view_channel=True, send_messages=True)
            await ctx.send(f'{user.name} has been added to the channel <#{channel.id}>')

    @commands.command(name='remove')
    async def remove(self, ctx, user: discord.member.Member):
        self.category = self.bot.get_channel(854455329503838258) if self.category is None else self.category
        channel_names = [channel.name for channel in self.category.text_channels]
        player_channel = 'hangman-' + ctx.message.author.name.lower()
        if user != ctx.message.author and player_channel in channel_names:
            channel = discord.utils.get(ctx.guild.channels, name=player_channel)
            await channel.set_permissions(user, overwrite=None)

    @commands.command(name='leave')
    async def leave(self, ctx):
        channel = ctx.message.channel
        self.category = self.bot.get_channel(854455329503838258) if self.category is None else self.category
        if channel != 'hangman' + ctx.message.author.name.lower() and ctx.message.channel in self.category.text_channels:
            await channel.set_permissions(ctx.message.author, view_channel=False)


# --------------------------------------------------------------------------- #

class ChannelSpecificText(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    @checks.admin_or_permissions(manage_server=True)
    async def cst(self, ctx, *, category: int = None):
        if category is None:
            return await ctx.send("You need to specify a category by ID")


# --------------------------------------------------------------------------- #

# Check that the bot is online and working.
@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


@bot.event
async def on_voice_state_update(member, before, after):
    # When the user changes channels
    if before.channel != after.channel:
        # If the user was previously in another voice channel, note the VC ID
        if before.channel is not None:
            prev_chan_id = before.channel.id
            prev_chan_name = (before.channel.name).replace(' ','-').lower()
        # If the user is joining another voice channel, note the VC ID
        if after.channel is not None:
            curr_chan = after.channel.id
            curr_chan_name = after.channel.name.replace(' ','-').lower()
        else:
            curr_chan_name = None
        # Note all of the existing text channels in Channel Specific Text category
        text_channel_list = []
        cat = discord.utils.get(member.guild.categories, id=829099747272687626)
        for channel in cat.text_channels:
            text_channel_list.append(channel.name)
        # If user was previously in a channel or disconnected, remove permissions
        if before.channel is not None or after.channel is None:
            text_chan = discord.utils.get(member.guild.text_channels, name=prev_chan_name, category=cat)
            if text_chan and text_chan.permissions_for(member).read_messages:
                await text_chan.set_permissions(member, overwrite=None)
            if len(before.channel.members) == 0:
                await text_chan.delete()
        # If channel specific text does not exist, create it and add permissions
        if curr_chan_name is not None and curr_chan_name not in text_channel_list:
            text_chan = await member.guild.create_text_channel(name=curr_chan_name, category=cat)
            await text_chan.set_permissions(member, view_channel=True)
        # If channel specific text already exists, just add permissions
        elif curr_chan_name in text_channel_list:
            text_chan = discord.utils.get(member.guild.text_channels, name=curr_chan_name)
            await text_chan.set_permissions(member, view_channel=True)
        else:
            pass


@bot.event
async def on_message(message):
    chan = message.channel
    user = message.author
    logs_chan = bot.get_channel(935729017410158623)
    if not bot_check(user) and chan.id != logs_chan.id and not message.content.startswith("-"):
        msgtosend = f"[{chan.name}] {user.name}: {message.content}"
        emb = message.embeds[0] if len(message.embeds) > 0 else None
        attach = await message.attachments[0].to_file() if len(message.attachments) > 0 else None
        await logs_chan.send(msgtosend, file=attach)
    await bot.process_commands(message)

###bot.add_cog(Hangman(bot, "dictionary.txt"))
###bot.add_cog(Blackjack(bot))
# bot.add_cog(Leaderboard(bot))
###bot.add_cog(Profile(bot))
###bot.add_cog(Help(bot))
###bot.add_cog(Gamble(bot))
bot.add_cog(Special(bot))
bot.run(TOKEN)
