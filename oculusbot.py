import os
import random
import discord
import requests
import openpyxl as xl
import math as m

from dotenv import load_dotenv
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions, MissingPermissions, Context

intents = discord.Intents.all()
intents.members = True

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
GUILD_ID = os.getenv('DISCORD_GUILD_ID')


# --------------------------------------------------------------------------- #

def update_user(user, index):
    excel = xl.load_workbook("users.xlsx")
    sheet = excel.active
    sheet['A' + str(index)] = str(user.id) if sheet['A' + str(index)].value is None else sheet['A' + str(index)].value
    sheet['B' + str(index)] = str(user.name) if sheet['B' + str(index)].value is None else sheet['B' + str(index)].value
    sheet['C' + str(index)] = str(1000) if sheet['C' + str(index)].value is None else sheet['C' + str(index)].value
    sheet['D' + str(index)] = str(0) if sheet['D' + str(index)].value is None else sheet['D' + str(index)].value
    sheet['E' + str(index)] = str(0) if sheet['E' + str(index)].value is None else sheet['E' + str(index)].value
    excel.save("users.xlsx")


def find_user(user):
    excel = xl.load_workbook("users.xlsx")
    sheet = excel.active
    first_column = sheet['A']
    ids = []
    index = 1
    for x in range(len(first_column)):
        ids.append(first_column[x].value)
        index += 1
        if str(user.id) == str(first_column[x].value):
            update_user(user, index-1)
            return index-1
    update_user(user, index-1)
    return index-1


def bot_check(member):
    return member.bot


def get_current(user, *argv):
    letters = []
    values = []
    for arg in argv:
        if arg == 'money':
            letters.append('C')
        elif arg == 'hmwins':
            letters.append('D')
        elif arg == 'hmmoney':
            letters.append('E')
        else:
            return
    index = find_user(user)
    excel = xl.load_workbook("users.xlsx")
    sheet = excel.active
    for x in range(len(letters)):
        values.append(sheet[letters[x] + str(index)].value)
    return values


def alter(user, amount, type):
    if type == 'money':
        letter = 'C'
    elif type == 'hmwins':
        letter = 'D'
    elif type =='hmmoney':
        letter = 'E'
    else:
        return
    index = find_user(user)
    excel = xl.load_workbook("users.xlsx")
    sheet = excel.active
    current_value = sheet[letter + str(index)].value
    new_value = int(current_value) + int(amount)
    sheet[letter + str(index)] = str(new_value)
    excel.save("users.xlsx")


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
                    alter(user, 50, 'money')
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
        await ctx.send(error)

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
                (user, -1 * int(bet), 'money')
                new_bal = get_current(user, 'money')[0]
                await ctx.send("{}... you're a loser. Your new balance is `${}`."
                               .format(username, new_bal))

    @flip.error
    async def flip_error(self, ctx, error):
        await ctx.send(error)

    @commands.command(name='setbal')
    @has_permissions(administrator=True)
    async def setbal(self, ctx, user: discord.member.Member, amount: int):
        index = find_user(user)
        excel = xl.load_workbook("users.xlsx")
        sheet = excel.active
        sheet['C' + str(index)] = str(amount)
        excel.save("users.xlsx")
        await ctx.send(f"{user.name}'s balance has been set to `${amount}`.")

    @setbal.error
    async def setbal_error(self, ctx, error):
        await ctx.send(error)

    @commands.command(name='resetmoney')
    @has_permissions(administrator=True)
    async def resetmoney(self, ctx):
        g = self.bot.get_guild(int(GUILD_ID))
        for user in g.members:
            if not bot_check(user):
                await self.setbal(ctx, user, 1000)

    @resetmoney.error
    async def resetmoney_error(self, ctx, error):
        await ctx.send(error)

    @commands.command(name='steal', help='Try to steal money from another user.')
    async def steal(self, ctx, amount: int, user: discord.member.Member):
        if not bot_check(user):
            thief = ctx.message.author
            thief_index = find_user(thief)
            peasant_index = find_user(user)
            peasant_balance = get_current(user, 'money')[0]
            thief_balance = get_current(thief, 'money')[0]
            if amount == 0:
                await ctx.send("Trying to steal $0? Wtf...")
            elif thief_index == peasant_index:
                await ctx.send("You cannot steal money from yourself.")
            elif amount > int(thief_balance):
                await ctx.send("Nah. Not enough money.")
            elif amount > int(peasant_balance):
                await ctx.send("Homie doesn't have enough money. Bruv kek.")
            else:
                chance = random.choice(range(0,100))
                if chance < 25:
                    alter(thief, amount, 'money')
                    alter(user, -amount, 'money')
                    await ctx.send(f'{thief.name} has stolen `${amount}` from {user.name} XD')
                else:
                    alter(thief, -amount, 'money')
                    alter(user, amount, 'money')
                    await ctx.send(f'{thief.name} tried to steal `${amount}` from {user.name} and failed ?XD')
        else:
            await ctx.send("You cannot steal money from a bot :/")

    @steal.error
    async def steal_error(self, ctx, error):
        await ctx.send(error)


# --------------------------------------------------------------------------- #


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.disp = discord.Embed(title="Money Leaderboard")
        self.msg = None
        self.active = False
        self.user = None
        self.id_money_list = []
        self.index = 0

    @commands.command(name='leaderboard', help='Show a money leaderboard', aliases=['rank', 'ranks', 'ldb'])
    async def leaderboard(self, ctx):
        if self.active:
            await self.msg.delete()
            self.cleanup()
        self.active = True
        self.user = ctx.message.author
        await ctx.message.delete()
        await self.calc_ranks(ctx)
        self.disp.set_thumbnail(url='https://i.imgur.com/VJ2brAT.png')
        await self.display(ctx)

    async def display(self, ctx):
        if self.msg is None:
            for num in range(10):
                new_id = self.id_money_list[self.index][1]
                user = await ctx.message.guild.fetch_member(int(new_id))
                username = user.name
                bal = self.id_money_list[self.index][0]
                self.disp.add_field(name="Rank {}:".format(self.index+1), value="{}:\t\t${}\n".format(username, bal), inline=False)
                self.index += 1
            curr_user = self.user.id
            counter = [element for i, element in self.id_money_list].index(int(curr_user))
            bal = get_current(self.user, 'money')[0]
            self.msg = await ctx.send("**`{}, you are currently ranked {}/{} with ${}.`**".format(self.user.name, counter+1, len(self.id_money_list), bal), embed=self.disp)
            await self.msg.add_reaction(emoji='⬅️')
            await self.msg.add_reaction(emoji='➡️')
            await self.msg.add_reaction(emoji='🔄')
            await self.msg.add_reaction(emoji='❌')
        else:
            for num in range(10):
                new_id = self.id_money_list[self.index][1]
                user = await ctx.message.guild.fetch_member(int(new_id))
                username = user.name
                bal = self.id_money_list[self.index][0]
                self.disp.set_field_at(index=num, name="Rank {}:".format(self.index+1), value="{}:\t\t${}\n".format(username, bal), inline=False)
                self.index += 1
            curr_user = self.user.id
            counter = [element for i, element in self.id_money_list].index(int(curr_user))
            bal = get_current(self.user, 'money')[0]
            await self.msg.edit(content="**`{}, you are currently ranked {}/{} with ${}.`**".format(self.user.name, counter+1, len(self.id_money_list), bal), embed=self.disp)

    async def calc_ranks(self, ctx):
        self.id_money_list = []
        async for user in ctx.message.author.guild.fetch_members():
            if not bot_check(user):
                balance = get_current(user, 'money')[0]
                index = find_user(user)
                excel = xl.load_workbook("users.xlsx")
                sheet = excel.active
                id_l = sheet['A' + str(index)].value
                new_list = [int(balance), int(id_l)]
                self.id_money_list.append(new_list)
        self.id_money_list.sort(reverse=True)

    def cleanup(self):
        self.disp = discord.Embed(title="Money Leaderboard")
        self.msg = None
        self.active = False
        self.id_money_list = []
        self.index = 0
        self.user = None

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if reaction.message == self.msg and not bot_check(user):
            self.user = user
            ctx = await self.bot.get_context(self.msg)
            await reaction.remove(user)
            if reaction.emoji == '⬅️':
                await self.calc_ranks(ctx)
                if self.index < 20:
                    pass
                else:
                    self.index -= 20
                    await self.display(ctx)
            elif reaction.emoji == '➡️':
                await self.calc_ranks(ctx)
                if self.index + 10 > len(self.id_money_list):
                    pass
                else:
                    await self.display(ctx)
            elif reaction.emoji == '🔄':
                await self.calc_ranks(ctx)
                if self.index > 0:
                    self.index -= 10
                await self.display(ctx)
            elif reaction.emoji == '❌':
                await self.msg.delete()
                self.cleanup()



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
        await bot.logout()

    @kill.error
    async def kill_error(self, ctx, error):
        await ctx.send(error)


# --------------------------------------------------------------------------- #


class Hangman(commands.Cog):
    def __init__(self, bot, path_to_dict):
        self.bot = bot
        self.game_in_progress = False
        self.player = None
        self.word = None
        f = open(path_to_dict, 'r')
        self.dict = f.readlines()
        f.close()
        self.stage = 0
        self.guessed = set()
        self.real_word = []
        self.wrong = []
        self.disp = discord.Embed(color=discord.Colour.darker_grey())
        self.msg = None
        self.authormsg = None
        self.botmsg = None
        self.win = False
        self.player = None
        self.prize = 2000
        self.set = None
        self.timer_check = False
        self.hmtop = discord.Embed(title="Hangman Top Stats", color=discord.Colour.darker_grey())
        self.topmsg = None
        self.id_win_list = []
        self.id_money_list = []
        self.images = [['https://i.imgur.com/bD68c54.png', 'https://i.imgur.com/Bi1S1r2.png', 'https://i.imgur.com/DKeCsD3.png', 'https://i.imgur.com/aSMmgDH.png', 'https://i.imgur.com/3pPsgr7.png', 'https://i.imgur.com/BCb26Ne.png'],
                       ['https://i.imgur.com/bD68c54.png', 'https://i.imgur.com/Bi1S1r2.png', 'https://i.imgur.com/DKeCsD3.png', 'https://i.imgur.com/aSMmgDH.png', 'https://i.imgur.com/3pPsgr7.png', 'https://i.imgur.com/BCb26Ne.png']]

    @commands.command(name='hangman', help='Start a game of hangman.',
                      aliases=['hm'])
    async def hm(self, ctx):
        if not self.game_in_progress:
            await ctx.message.delete()
            self.player = ctx.message.author
            self.game_in_progress = True
            self.word = random.choice(self.dict).rstrip()
            print(f"Hangman word: {self.word}")
            self.real_word = ['_' for i in range(len(self.word))]
            self.set = random.choice(range(len(self.images))) - 1
            self.timer.start(ctx)
            await self.display(ctx)
        else:
            await ctx.message.delete()
            await self.clear_msg()
            self.authormsg = ctx.message
            self.botmsg = await ctx.send('A game of hangman is already in progress!')

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
        await ctx.message.delete()
        await self.cleanuptop()
        await self.calc_ranks(ctx)
        wins_msg, money_msg = '```', '```'
        for num in range(3):
            win_member = await ctx.message.guild.fetch_member(int(self.id_win_list[num][1]))
            win_user = win_member.name
            money_member = await ctx.message.guild.fetch_member(int(self.id_money_list[num][1]))
            money_user = money_member.name
            wins = self.id_win_list[num][0]
            money = self.id_money_list[num][0]
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
        self.id_win_list = []
        self.id_money_list = []

    async def calc_ranks(self, ctx):
        self.id_win_list = []
        self.id_money_list = []
        async for user in ctx.message.author.guild.fetch_members():
            if not bot_check(user):
                values = get_current(user, 'hmwins', 'hmmoney')
                index = find_user(user)
                excel = xl.load_workbook("users.xlsx")
                sheet = excel.active
                id_l = sheet['A' + str(index)].value
                new_list = [int(values[0]), int(id_l)]
                new_list2 = [int(values[1]), int(id_l)]
                self.id_win_list.append(new_list)
                self.id_money_list.append(new_list2)
        self.id_win_list.sort(reverse=True)
        self.id_money_list.sort(reverse=True)

    @commands.command(name='guess', help='Guess a letter.',
                      aliases=['g'])
    async def guess(self, ctx, letter: str):
        letter = letter.lower()
        if self.game_in_progress and self.player == ctx.message.author:
            await self.clear_msg()
            self.authormsg = ctx.message
            if len(letter) > 1:
                self.botmsg = await ctx.send('Your guess must be 1 character!')
            elif letter not in self.guessed:
                self.guessed.add(letter)
                if letter in self.word:
                    self.botmsg = await ctx.send('Good guess!')
                    for i in range(len(self.word)):
                        if self.word[i:i+1] == letter:
                            self.real_word[i] = letter
                else:
                    self.botmsg = await ctx.send('Bad guess...')
                    self.stage += 1
                    self.wrong.append(letter)
            else:
                self.botmsg = await ctx.send('You have already guessed that!')
            potential_win = ''.join(self.real_word)
            if potential_win == self.word:
                self.win = True
            await self.display(ctx)

    @guess.error
    async def guess_error(self, ctx, error):
        self.authormsg = ctx.message
        self.botmsg = await ctx.send(error)

    @commands.command(name='answer', help='Guess the word.')
    async def answer(self, ctx, word: str):
        word = word.lower()
        if self.game_in_progress and self.player == ctx.message.author:
            await self.clear_msg()
            self.authormsg = ctx.message
            if word == self.word:
                self.botmsg = await ctx.send('NICE!')
                self.win = True
            else:
                self.botmsg = await ctx.send('Bad guess...')
                self.stage += 1
            await self.display(ctx)

    @answer.error
    async def answer_error(self, ctx, error):
        self.authormsg = ctx.message
        self.botmsg = await ctx.send(error)

    @commands.command(name='end', help='End the current game.')
    async def end(self, ctx):
        await self.clear_msg()
        if self.game_in_progress and self.player == ctx.message.author:
            await ctx.send(f'You have decided to end the game early. The word was: {self.word}.')
            self.cleanup()
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

    def cleanup(self):
        self.game_in_progress = False
        self.stage = 0
        self.guessed = set()
        self.real_word = []
        self.wrong = []
        self.msg = None
        self.authormsg = None
        self.botmsg = None
        self.player = None
        self.disp = discord.Embed(color=discord.Colour.darker_grey())
        self.win = False
        self.prize = 2000
        self.set = 0
        self.timer_check = False
        self.timer_end()
        return

    async def display(self, ctx):
        wrd = '``` ' + ''.join([let+' ' for let in self.word]) + '```' if self.win else '``` ' + ''.join([let+' ' for let in self.real_word]) + '```'
        guessed = ''.join([let+' ' for let in self.guessed])
        self.stage = len(self.images[self.set]) - 1 if self.win else self.stage
        self.disp.title = 'HANGMAN'
        self.disp.description = wrd
        self.disp.set_thumbnail(url=self.player.avatar_url)
        self.disp.set_image(url=self.images[self.set][self.stage])
        self.disp.set_footer(text=f'» Letters guessed: {guessed}')
        if self.msg is None:
            #self.disp.add_field(name='Word to Guess', value=wrd)
            self.msg = await ctx.send('Use `-guess <letter>` or `-answer <word>` to guess.', embed=self.disp)
        else:
            #self.disp.set_field_at(index=0, name='Word to Guess', value=wrd)
            await self.msg.edit(embed=self.disp)
        if self.win:
            if len(self.wrong) > 0:
                self.prize -= m.floor(self.prize * float(len(self.wrong)/10))
            await self.clear_msg()
            alter(self.player, self.prize, 'money')
            alter(self.player, 1, 'hmwins')
            alter(self.player, self.prize, 'hmmoney')
            bal = get_current(self.player, 'money')[0]
            await ctx.send(f"Congratulations {self.player.name}, you guessed the word and earned `${self.prize}`! You now have `${bal}`.")
            self.cleanup()
        if self.stage == len(self.images[self.set]) - 1:
            await self.clear_msg()
            await ctx.send(f"{self.player.name}... you lost! The word was: `{self.word}`")
            self.cleanup()

    @tasks.loop(minutes=5.0)
    async def timer(self, ctx):
        if self.timer_check:
            await ctx.send(f'{self.player.name}, your game timed out!')
            self.cleanup()
        else:
            self.timer_check = True

    def timer_end(self):
        self.timer.cancel()

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
        await ctx.message.delete()
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
        await ctx.message.delete()
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
        elif option is None:
            await self.display(ctx)
        else:
            return

    async def hm(self, ctx):
        self.disp.add_field(name='\u200b', value='```-hangman, -hm```» Start a game of Hangman.', inline=False)
        self.disp.add_field(name='\u200b', value='```-guess [letter], -g [letter]```» Guess a letter.', inline=False)
        self.disp.add_field(name='\u200b', value='```-answer [word]```» Guess the entire word.', inline=False)
        self.disp.add_field(name='\u200b', value='```-endhangman, -endhm```» End your game of Hangman early.', inline=False)
        self.disp.add_field(name='\u200b', value='```-hmstats [user]```» Show Hangman stats for a user.', inline=False)
        self.disp.add_field(name='\u200b', value='```-hmtop```» Show the top 3 Hangman players.', inline=False)
        self.msg = await ctx.send(embed=self.disp)

    async def gamb(self, ctx):
        self.disp.add_field(name='\u200b', value="```-money [user], -bal [user]```» Check a user's balance.", inline=False)
        self.disp.add_field(name='\u200b', value="```-pay [amount] [user], -give [amount] [user]```» Send money to another user.", inline=False)
        self.disp.add_field(name='\u200b', value="```-coinflip [amount], -flip [amount], -cf [amount]```» Double your money with a 50/50 chance.", inline=False)
        self.disp.add_field(name='\u200b', value="```-steal [amount] [user]```» Attempt to steal money from another user.", inline=False)
        self.disp.add_field(name='\u200b', value="```-leaderboard, -ldb, -rank```» Show a leaderboard based on money.", inline=False)
        self.msg = await ctx.send(embed=self.disp)

    async def bj(self, ctx):
        self.disp.add_field(name='\u200b', value="```-blackjack [amount], -bj [amount]```» Start a game of Blackjack.", inline=False)
        self.disp.add_field(name='\u200b', value="```-endblackjack, -endbj```» End your game of Blackjack early .", inline=False)
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

        self.decks = 4 * 4
        self.cards = [self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks]
        self.deck = ["2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟", "🇯", "🇶", "🇰", "🇦"]
        self.cardsleft = sum(self.cards)

    @commands.command(name='blackjack', help='Play a game of blackjack.',
                      aliases=['bj'])
    async def blackjack(self, ctx, buyin: str):
        await ctx.message.delete()
        if ctx.message.author not in self.player:
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
                self.player_value[index] += self.get_value(player_first, self.player, index)
                self.player_value[index] += self.get_value(player_second, self.player, index)
                # self.timer.start(ctx)
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

    @commands.command(name='endblackjack', aliases=['endbj'])
    async def endbj(self, ctx):
        await ctx.message.delete()
        if ctx.message.author in self.player:
            index = self.player.index(ctx.message.author)
            alter(self.player[index], self.buyin[index], 'money')
            await ctx.send(f'You have decided to fold.')
            self.cleanup(index)
        else:
            await ctx.send('You do not have an active game of Blackjack.')

    def pick_rand(self):
        self.resetdeck() if self.cardsleft == 0 else None
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
        self.cards = [self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks]
        self.cardsleft = sum(self.cards)

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
            index = self.player.index(user)
            ctx = await self.bot.get_context(self.msg[index])
            if reaction.emoji == '✅':
                await reaction.remove(user)
                await self.hit(ctx, user, index)
                await self.display(ctx, index)
            elif reaction.emoji == '❌':
                await reaction.remove(user)
                await self.hit(ctx, None, index)
                await self.display(ctx, index)


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
