import os
import random
import discord
import requests
import openpyxl as xl
import pandas as p
import math as m
import asyncio

from dotenv import load_dotenv
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions, MissingPermissions, Context

intents = discord.Intents.all()
intents.members = True

spreadsheet = 'users.xlsx'

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
GUILD_ID = os.getenv('DISCORD_GUILD_ID')


# --------------------------------------------------------------------------- #

def bot_check(member):
    return member.bot

def find_user(user):
    df = p.read_excel(spreadsheet)
    df = df.astype(str)
    index = df[df['ids']==str(user.id)].index.values
    if len(index) == 0:
        index = [int(df.iloc[-1].name)+1]
        df = df.append(p.DataFrame([[str(index[0]), str(user.id), str(user.name), str(1000), str(0), str(0)]], columns=['index', 'ids', 'names', 'money', 'hmwins', 'hmmoney']), ignore_index=True)
        df.to_excel(spreadsheet, index=False)
    return index[0]

def alter(user, amount, type):
    df = p.read_excel(spreadsheet)
    df = df.astype(str)
    index = find_user(user)
    new_value = int(df.iloc[index][str(type)]) + int(amount)
    df.loc[int(index), str(type)] = str(new_value)
    df.to_excel(spreadsheet, index=False)

def get_current(user, *argv):
    values = []
    index = find_user(user)
    df = p.read_excel(spreadsheet)
    df = df.astype(str)
    for arg in argv:
        values.append(df.iloc[index][str(arg)])
    values.append(index)
    return values


class Gamble(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.free_money.start()
        self.timer_check = False

    # Gives every user $5 every 10 minutes the bot is online.
    @tasks.loop(minutes=10.0)
    async def free_money(self):
        if self.timer_check:
            g = bot.get_guild(int(GUILD_ID))
            for user in g.members:
                if not bot_check(user):
                    alter(user, 25, 'money')
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
            balance = get_current(user, 'money')[0]
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
        await ctx.send('Format: -money [user]')

    # Give some money to another player.
    @commands.command(name='pay', help="Pay another user some money.",
                      aliases=['give'])
    async def pay(self, ctx, amount: int, user: discord.member.Member):
        if not bot_check(user):
            sender = ctx.message.author
            sender_index = find_user(sender)
            rec_index = find_user(user)
            sender_balance = get_current(sender, 'money')[0]
            if sender_index == rec_index:
                await ctx.send("You cannot send money to yourself.")
            elif amount > int(sender_balance):
                await ctx.send("You are too poor. You only have `${}`."
                               .format(sender_balance))
            else:
                rec_balance = get_current(user, 'money')[0]
                alter(sender, -amount, 'money')
                alter(user, amount, 'money')
                await ctx.send("You have paid `${}` to {}.".format(amount, user.name))
        else:
            await ctx.send("You cannot send money to a bot!")

    @pay.error
    async def pay_error(self, ctx, error):
        await ctx.send('Format: -pay [amount] [user]')

    # Gamble via 50/50 chances.
    @commands.command(name='coinflip', help="Bet money on a coin flip.",
                      aliases=['flip', 'cf'])
    async def flip(self, ctx, bet: str):
        user = ctx.message.author
        username = ctx.message.author.name
        balance = get_current(user, 'money')[0]
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
                alter(user, bet, 'money')
                new_bal = get_current(user, 'money')[0]
                await ctx.send("{}, you won! Your new balance is `${}`."
                               .format(username, new_bal))
            else:
                alter(user, -1 * int(bet), 'money')
                new_bal = get_current(user, 'money')[0]
                await ctx.send("{}... you're a loser. Your new balance is `${}`."
                               .format(username, new_bal))

    @flip.error
    async def flip_error(self, ctx, error):
        await ctx.send('Format: -flip [amount]')

    @commands.command(name='setbal')
    @has_permissions(administrator=True)
    async def setbal(self, ctx, user: discord.member.Member, amount: int):
        index = find_user(user)
        df = p.read_excel(spreadsheet)
        df = df.astype(str)
        df.loc[int(index), 'money'] = str(amount)
        df.to_excel(spreadsheet, index=False)
        await ctx.send(f"{user.name}'s balance has been set to `${amount}`.")

    @setbal.error
    async def setbal_error(self, ctx, error):
        print(error)

    @commands.command(name='resetmoney')
    @has_permissions(administrator=True)
    async def resetmoney(self, ctx):
        g = self.bot.get_guild(int(GUILD_ID))
        for user in g.members:
            if not bot_check(user):
                await self.setbal(ctx, user, 1000)

    @resetmoney.error
    async def resetmoney_error(self, ctx, error):
        print(error)


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
        counter = find_user(self.user)
        if self.msg is None:
            for num in range(10):
                username = df.iloc[self.index]['names']
                bal = df.iloc[self.index]['money']
                self.disp.add_field(name="Rank {}:".format(self.index+1), value="{}:\t\t${}\n".format(username, bal), inline=False)
                self.index += 1
            bal = get_current(self.user, 'money')[0]
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
            bal = get_current(self.user, 'money')[0]
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


error_message = 'An unknown error occurred. Sorry!'


class Join(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Assign the role for on_member_join
    @commands.command(name='joinrole', help='Sets the role for new members.')
    @has_permissions(administrator=True, manage_roles=True)
    async def set_join_role(self, ctx, role: str):
        role_check = discord.utils.get(ctx.message.author.guild.roles,
                                       name=role)
        if type(role_check) is not None:
            f = open("roles/joinrole.txt", "w")
            role_id = str(role_check.id)
            f.write(role_id)
            f.close()
            await ctx.send("New members will now be given the role `{}` when "
                           "they join the server.".format(role))
        else:
            await ctx.send('The specified role does not exist.')

    @set_join_role.error
    async def set_join_role_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            await ctx.send("Sorry {}, you do not have permissions to do "
                           "that.".format(ctx.message.author.name))
        else:
            await ctx.send(error_message)

    # Assign the channel for on_member_join
    @commands.command(name='joinchannel', help="Sets the channel to welcome "
                                               "new members.")
    @has_permissions(administrator=True, manage_channels=True)
    async def set_join_channel(self, ctx, channel: str):
        channel_check = discord.utils.get(ctx.message.author.guild.text_channels, name=channel)
        if type(channel_check) is not None:
            f = open("roles/joinchannel.txt", "w")
            channel_id = str(channel_check.id)
            f.write(channel_id)
            f.close()
            await ctx.send("Welcome messages will now be sent in the text "
                           "channel: `{}`.".format(channel))
        else:
            await ctx.send('The specified channel does not exist.')

    @set_join_channel.error
    async def set_join_channel_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            await ctx.send("Sorry {}, you do not have permissions to do that."
                           .format(ctx.message.author.name))
        else:
            await ctx.send(error_message)

    # Sets the welcome message for new members.
    @commands.command(name='welcomemsg', help="Sets the welcome message for "
                                              "new members.")
    @has_permissions(administrator=True, manage_messages=True)
    async def set_welcome_msg(self, ctx, msg: str):
        f = open("roles/welcomemsg.txt", "w")
        f.write(msg)
        f.close()
        await ctx.send("The welcome message has now been updated to: "
                       "`{}`.".format(msg))

    @set_welcome_msg.error
    async def set_welcome_msg_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            await ctx.send("Sorry {}, you do not have permissions to do "
                           "that.".format(ctx.message.author.name))
        else:
            await ctx.send(error_message)


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
        await ctx.send(error)


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
        roles.reverse()
        for role in roles:
            self.roles.append(role.name)
        self.rolenames = ''.join([let+', ' for let in self.roles])
        self.rolenames = self.rolenames[:-2]
        await self.display(ctx) if not bot_check(self.user) else await ctx.send("Bots are fake and don't have profiles.")

    async def display(self, ctx):
        self.disp.title = self.user.nick if self.user.nick is not None else self.user.name
        self.disp.add_field(name='Balance', value=f"${get_current(self.user, 'money')[0]}", inline=False)
        self.disp.add_field(name='Hangman Stats', value=f"Wins: {get_current(self.user, 'hmwins')[0]}\nEarnings: ${get_current(self.user, 'hmmoney')[0]}", inline=False)
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


class Role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.disp = discord.Embed(color=discord.Colour.red())

    @commands.command(name='setmsg')
    @has_permissions(administrator=True)
    async def setrolemsg(self, ctx, chan: discord.TextChannel):
        self.disp.add_field(name='Reaction Role', value='`yeet`')
        msg = await chan.send(embed=self.disp)
        f = open("roles/rolemsg.txt", "w")
        f.write(str(chan) + " - " + str(msg.id))
        f.close()
        await ctx.send("Role message set.")

    @commands.command(name='addrole')
    @has_permissions(administrator=True)
    async def addrole(self, ctx, emoji: str, role: discord.Role):
        exists = False
        f = open("roles/roles.txt", "r")
        for line in f.readlines():
            print(line)
            if str(role) in line:
                exists = True
        f.close()
        if not exists:
            f = open("roles/roles.txt", "a+")
            f.write(str(role) + " - " + str(emoji) + "\n")
            f.close()
            await self.display(ctx, emoji, role)
            await ctx.send(f"Role `{role}` added.")
        else:
            await ctx.send("Role already exists.")

    def display(self, ctx, emoji, role):
        pass


# --------------------------------------------------------------------------- #


class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.disp = []
        self.player = []
        self.dealer_hand_real = []
        self.dealer_hand = []
        self.dealer_value = []
        self.player_hand = []
        self.player_value = []
        self.playeraces = []
        self.dealeraces = []
        self.msg = []
        self.end = []
        self.prize = []
        self.buyin = []
        self.active = 0
        self.decks = 4 * 4
        self.cards = [self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks]
        self.deck = ["2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟", "🇯", "🇶", "🇰", "🇦"]
        self.cardsleft = sum(self.cards)

    @commands.command(name='blackjack', help='Play a game of blackjack.',
                      aliases=['bj'])
    async def blackjack(self, ctx, buyin: str):
        if ctx.message.author not in self.player:
            if self.active > 0:
                await asyncio.sleep(self.active*1.5)
            self.active += 1
            index = len(self.player)
            self.disp.append(discord.Embed(color=discord.Colour.blue()))
            self.player.append(ctx.message.author)
            self.dealer_hand_real.append('')
            self.dealer_hand.append('❓')
            self.dealer_value.append(0)
            self.player_hand.append('')
            self.player_value.append(0)
            self.playeraces.append(0)
            self.dealeraces.append(0)
            self.end.append(False)
            self.msg.append(None)
            balance = get_current(self.player[index], 'money')[0]
            if buyin.lower() == 'all':
                buyin = balance
            if int(buyin) > int(balance):
                await ctx.send("You do not have that much money.")
            elif int(buyin) == 0:
                await ctx.send("You cannot play for $0.")
            else:
                alter(self.player[index], -1 * int(buyin), 'money')
                self.prize.append(int(buyin) * 2)
                self.buyin.append(int(buyin))
                dealer_first = self.pick_rand()
                dealer_second = self.pick_rand()
                self.dealer_hand_real[index] += dealer_first + ' '
                self.dealer_hand_real[index] += dealer_second
                self.dealer_hand[index] += dealer_second
                self.dealer_value[index] += self.get_value(dealer_first, None, index)
                self.dealer_value[index] += self.get_value(dealer_second, None, index)
                player_first = self.pick_rand()
                player_second = self.pick_rand()
                self.player_hand[index] += player_first + ' '
                self.player_hand[index] += player_second
                self.player_value[index] += self.get_value(player_first, self.player[index], index)
                self.player_value[index] += self.get_value(player_second, self.player[index], index)
                await self.display(ctx, index)
        else:
            await ctx.send('You are already playing a game of Blackjack!')

    async def display(self, ctx, index):
        player = f"**{self.player[index].name}'s Hand**"
        if self.end[index]:
            dealer_hand = self.dealer_hand_real[index]
        else:
            dealer_hand = self.dealer_hand[index]
        print(f'Dealer = {self.dealer_value[index]}, {self.player[index].name} = {self.player_value[index]}')
        self.cardsleft = sum(self.cards)
        self.disp[index].title = f'BLACKJACK'
        self.disp[index].set_thumbnail(url=self.player[index].avatar_url)
        self.disp[index].set_footer(text=f'» Number of Decks: {int(self.decks/4)}\n» Cards Remaining: {self.cardsleft}\n» ${self.buyin[index]} bet')
        if self.msg[index] is None:
            self.disp[index].add_field(name="**Dealer's Hand**", value=f'> {dealer_hand}', inline=False)
            self.disp[index].add_field(name=player, value=f'> {self.player_hand[index]}')
            self.msg[index] = await ctx.send('Use the reactions to hit (✅) or stay (❌).', embed=self.disp[index])
            await self.msg[index].add_reaction(emoji='✅')
            await self.msg[index].add_reaction(emoji='❌')
        else:
            self.disp[index].set_field_at(index=0, name="**Dealer's Hand**", value=f'> {dealer_hand}', inline=False)
            self.disp[index].set_field_at(index=1, name=player, value=f'> {self.player_hand[index]}')
            await self.msg[index].edit(embed=self.disp[index])
        if self.end[index]:
            if self.dealer_value[index] == self.player_value[index] and self.dealer_value[index] <= 21:
                alter(self.player[index], self.buyin[index], 'money')
                bal = get_current(self.player[index], 'money')[0]
                msg = f'{self.player[index].name}, you tied with the dealer. Your original buy-in is returned to you. Your balance is `${bal}`.'
            elif (self.dealer_value[index] <= 21 and (self.dealer_value[index] >= self.player_value[index] or self.player_value[index] > 21)) or (self.dealer_value[index] > 21 and self.player_value[index] > 21):
                bal = get_current(self.player[index], 'money')[0]
                msg = f'Tough luck {self.player[index].name}, the dealer outplayed you. You now have `${bal}`.'
            else:
                alter(self.player[index], self.prize[index], 'money')
                bal = get_current(self.player[index], 'money')[0]
                msg = f"Nice job on that W, {self.player[index].name}! You win `${self.prize[index]}`. Your new balance is `${bal}`."
            await ctx.send(msg)
            self.cleanup(index)
        self.active -= 1

    @commands.command(name='endblackjack', aliases=['endbj', 'bjend', 'blackjackend'])
    async def endbj(self, ctx):
        if ctx.message.author in self.player:
            index = self.player.index(ctx.message.author)
            alter(self.player[index], self.buyin[index], 'money')
            await ctx.send(f'You have decided to fold.')
            self.cleanup(index)
        else:
            await ctx.send('You do not have an active game of Blackjack.')

    def pick_rand(self):
        self.resetdeck() if self.cardsleft < 4 else None
        index = random.choice(range(0, len(self.deck)))
        choice = self.deck[index] if self.cards[index] != 0 else self.pick_rand()
        self.cards[index] -= 1 if self.cards[index] != 0 else 0
        return choice

    def cleanup(self, index):
        del self.disp[index]
        del self.player[index]
        del self.dealer_hand_real[index]
        del self.dealer_hand[index]
        del self.dealer_value[index]
        del self.player_hand[index]
        del self.player_value[index]
        del self.playeraces[index]
        del self.dealeraces[index]
        del self.msg[index]
        del self.end[index]
        del self.prize[index]
        del self.buyin[index]
        return

    def resetdeck(self):
        self.decks = 4 * 4
        for x in range(len(self.cards)):
            self.cards[x] = self.decks
        self.cardsleft = sum(self.cards)
        return

    def get_value(self, string, player, index):
        try:
            value = int(string[0])
        except:
            if string[0] == '🇦':
                value = 11
                if player == self.player[index]:
                    self.playeraces[index] += 1
                else:
                    self.dealeraces[index] += 1
            else:
                value = 10
        return int(value)

    async def hit(self, ctx, player, index):
        if player == self.player[index]:
            new_card = self.pick_rand()
            self.player_hand[index] += ' ' + new_card
            self.player_value[index] += self.get_value(new_card, self.player[index], index)
            if self.player_value[index] > 21 and self.playeraces[index] > 0:
                self.playeraces[index] -= 1
                self.player_value[index] -= 10
            elif self.player_value[index] > 21:
                await self.hit(ctx, None, index)
        else:
            if self.dealer_hand_real[index] == '🇦🇦':
                self.dealeraces[index] -= 1
                self.dealer_value[index] -= 10
            while(self.dealer_value[index] < 17):
                new_card = self.pick_rand()
                self.dealer_hand[index] += ' ' + new_card
                self.dealer_hand_real[index] += ' ' + new_card
                self.dealer_value[index] += self.get_value(new_card, None, index)
                if self.dealer_value[index] > 21 and self.dealeraces[index] > 0:
                    self.dealeraces[index] -= 1
                    self.dealer_value[index] -= 10
            self.end[index] = True

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user in self.player:
            if self.active > 0:
                await asyncio.sleep(self.active*1.5)
            index = self.player.index(user)
            ctx = await self.bot.get_context(self.msg[index])
            if reaction.emoji == '✅':
                self.active += 1
                await reaction.remove(user)
                await self.hit(ctx, user, index)
                await self.display(ctx, index)
            elif reaction.emoji == '❌':
                self.active += 1
                await reaction.remove(user)
                await self.hit(ctx, None, index)
                await self.display(ctx, index)


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

    @commands.command(name='hangman', help='Start a game of hangman.',
                      aliases=['hm'])
    async def hm(self, ctx):
        if ctx.message.author not in self.player:
            if self.active > 0:
                await asyncio.sleep(self.active*1.5)
            self.active += 1
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
            values = get_current(user, 'hmwins', 'hmmoney')
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
        if self.active > 0:
            await asyncio.sleep(self.active*1.5)
        letter = letter.lower()
        index = self.player.index(ctx.message.author)
        if self.player[index] == ctx.message.author and ctx.message.channel == self.channel[index]:
            self.active += 1
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
        if self.active > 0:
            await asyncio.sleep(self.active*1.5)
        word = word.lower()
        index = self.player.index(ctx.message.author)
        if self.player[index] == ctx.message.author and ctx.message.channel == self.channel[index]:
            self.active += 1
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
            alter(self.player[index], self.prize[index], 'money')
            alter(self.player[index], 1, 'hmwins')
            alter(self.player[index], self.prize[index], 'hmmoney')
            bal = get_current(self.player[index], 'money')[0]
            await ctx.send(f"Congratulations {self.player[index].name}, you guessed the word and earned `${self.prize[index]}`! You now have `${bal}`.")
            self.cleanup(index)
            return
        if self.stage[index] == len(self.images[self.set[index]]) - 1:
            await self.clear_msg()
            await ctx.send(f"{self.player[index].name}... you lost! The word was: `{self.word[index]}`")
            self.cleanup(index)
        self.active -= 1

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
            await channel.set_permissions(user, view_channel=False)

    @commands.command(name='leave')
    async def leave(self, ctx):
        channel = ctx.message.channel
        self.category = self.bot.get_channel(854455329503838258) if self.category is None else self.category
        if channel != 'hangman' + ctx.message.author.name.lower() and ctx.message.channel in self.category.text_channels:
            await channel.set_permissions(ctx.message.author, view_channel=False)


# --------------------------------------------------------------------------- #


bot = commands.Bot(command_prefix='-', intents=intents, case_insensitive=True)
bot.remove_command('help')

# Check that the bot is online and working.
@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


# Welcome users when they join and auto-assign a role.
@bot.event
async def on_member_join(member):
    f = open("roles/joinrole.txt", "r")
    role_id = f.read(18)
    role = discord.utils.get(member.guild.roles, id=int(role_id))
    f.close()
    await member.add_roles(role)
    f = open("roles/joinchannel.txt", "r")
    channel_id = f.read(18)
    channel = discord.utils.get(member.guild.text_channels, id=int(channel_id))
    f.close()
    f = open("roles/welcomemsg.txt", "r")
    welcome_msg = str(f.read())
    f.close()
    await channel.send(welcome_msg.format(member.name))


@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel != after.channel:
        if before.channel is not None:
            prev_chan_id = before.channel.id
            prev_chan_name = (before.channel.name).replace(' ','-').lower()
        if after.channel is not None:
            curr_chan = after.channel.id
            curr_chan_name = after.channel.name.replace(' ','-').lower()
        else:
            curr_chan_name = None
        text_channel_list = []
        for channel in member.guild.text_channels:
            text_channel_list.append(channel.name)
        if before.channel is not None or after.channel is None:
            text_chan = discord.utils.get(member.guild.text_channels, name=prev_chan_name)
            if text_chan and text_chan.permissions_for(member).read_messages:
                await text_chan.set_permissions(member, view_channel=False)
        if curr_chan_name is not None and curr_chan_name not in text_channel_list:
            cat = discord.utils.get(member.guild.categories, id=829099747272687626)
            text_chan = await member.guild.create_text_channel(name=curr_chan_name, category=cat)
            await text_chan.set_permissions(member, view_channel=True)
        elif curr_chan_name in text_channel_list:
            text_chan = discord.utils.get(member.guild.text_channels, name=curr_chan_name)
            await text_chan.set_permissions(member, view_channel=True)
        else:
            pass

bot.add_cog(Help(bot))
bot.add_cog(Profile(bot))
bot.add_cog(Gamble(bot))
bot.add_cog(Leaderboard(bot))
bot.add_cog(Blackjack(bot))
bot.add_cog(Join(bot))
bot.add_cog(Special(bot))
bot.add_cog(Hangman(bot, "dictionary.txt"))
bot.add_cog(Role(bot))
bot.run(TOKEN)
