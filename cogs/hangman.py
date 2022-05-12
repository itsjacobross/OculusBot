import discord
import sqlite3 as sq
import random
import datetime
import math as m

from discord.ext import commands, tasks


class Hangman(commands.Cog):
    def __init__(self, bot, path_to_dict):
        self.bot = bot
        self.word = []
        f = open(path_to_dict, 'r')
        self.words = f.readlines()
        f.close()

        self.dict = {}
        self.conn = sq.connect('database.db')
        self.c = self.conn.cursor()
        self.images = [['https://i.imgur.com/bD68c54.png', 'https://i.imgur.com/Bi1S1r2.png', 'https://i.imgur.com/DKeCsD3.png', 'https://i.imgur.com/aSMmgDH.png', 'https://i.imgur.com/3pPsgr7.png', 'https://i.imgur.com/BCb26Ne.png'],
                       ['https://i.imgur.com/bD68c54.png', 'https://i.imgur.com/Bi1S1r2.png', 'https://i.imgur.com/DKeCsD3.png', 'https://i.imgur.com/aSMmgDH.png', 'https://i.imgur.com/3pPsgr7.png', 'https://i.imgur.com/BCb26Ne.png']]
        self.check_hangman_activity.start()
        self.timer_check = False

    # Checks for inactive hangman channels every hour.
    @tasks.loop(minutes=60.0)
    async def check_hangman_activity(self):
        for guild in self.bot.guilds:
            self.c.execute('''SELECT hm_category
                              FROM servers
                              WHERE guild_id=?''',
                           (int(guild.id),))
            hm_category = self.c.fetchone()[0]
            if hm_category is not None:
                if self.timer_check:
                    for text_channel in self.bot.get_channel(int(hm_category)).text_channels:
                        messages = await text_channel.history(after=(datetime.datetime.now() - datetime.timedelta())).flatten()
                        if len(messages) == 0:
                            await text_channel.delete()
                else:
                    self.timer_check = True

    @commands.command(name='hangman', help='Start a game of hangman.',
                      aliases=['hm'])
    async def hm(self, ctx):
        guildid = ctx.message.guild.id
        user = ctx.message.author
        if (guildid, user.id) not in self.dict:
            word = random.choice(self.words).rstrip()
            data = {"display": discord.Embed(color=discord.Colour.darker_grey()),
                    "msg": None,
                    "win": False,
                    "prize": 2000,
                    "stage": 0,
                    "word": word,
                    "real_word": ['_' for i in range(len(word))],
                    "guessed": set(),
                    "wrong": [],
                    "set": random.choice(range(len(self.images))) - 1,
                    "text_channel": ctx.message.channel,
                    "authormsg": None,
                    "botmsg": None
                    }
            self.dict[(guildid, user.id)] = data
            print(f"{user.name}'s Hangman word: {self.dict[(guildid, user.id)]['word']}")

            self.c.execute('''SELECT hm_category
                              FROM servers
                              WHERE guild_id=?''',
                           (int(guildid),))
            hm_category = self.c.fetchone()[0]

            if hm_category is not None:
                text_channel_list = []
                category = self.bot.get_channel(int(hm_category))
                for channel in category.text_channels:
                    text_channel_list.append(channel.name)
                player_channel = 'hangman-' + user.name.lower()
                if player_channel not in text_channel_list:
                    new_chan = await category.create_text_channel(player_channel)
                    self.dict[(guildid, user.id)]["text_channel"] = new_chan
                    await new_chan.edit(topic=('See additional hangman commands with -help hangman'))
                else:
                    self.dict[(guildid, user.id)]["text_channel"] = discord.utils.get(ctx.guild.channels, name=player_channel)
                await ctx.send(f'Starting your game of Hangman in <#{self.dict[(guildid, user.id)]["text_channel"].id}>')
            await self.dict[(guildid, user.id)]["text_channel"].set_permissions(user, view_channel=True, send_messages=True)
            await self.display(self.dict[(guildid, user.id)]["text_channel"], user)
        else:
            await self.clear_msg(guildid, user)
            self.authormsg = ctx.message
            self.botmsg = await ctx.send('You already have an active game of Hangman!')

    @commands.command(name='hmstats')
    async def hmstats(self, ctx, user: discord.member.Member = None):
        user = ctx.message.author if user is None else user
        if not user.bot:
            hmstats = discord.Embed(title=f"{user.name}'s Hangman Stats", color=discord.Colour.darker_grey())
            guildid = ctx.message.guild.id
            self.c.execute('''SELECT hmwins, hmmoney
                              FROM users
                              WHERE (guild_id=? AND user_id=?)''',
                           (int(guildid), int(user.id)))
            server_values = self.c.fetchone()
            self.c.execute('''SELECT SUM(hmwins), SUM(hmmoney)
                              FROM users
                              WHERE user_id=?''',
                           (int(user.id),))
            total_values = self.c.fetchone()
            guild_stats = f"Wins: {server_values[0]}\nEarnings: ${server_values[1]}"
            total_stats = f"Wins: {total_values[0]}\nEarnings: ${total_values[1]}"

            hmstats.add_field(name=f"{ctx.message.guild.name} Stats", value=guild_stats, inline=False)
            hmstats.add_field(name="Total Stats", value=total_stats, inline=False)
            hmstats.set_thumbnail(url=user.avatar_url)
            await ctx.send(embed=hmstats)
        else:
            await ctx.send("Bots don't play hangman lol!")

    @commands.command(name='hmtop')
    async def hmtop(self, ctx):
        hmtop = discord.Embed(title=f"{ctx.guild.name} Hangman Top Stats", color=discord.Colour.darker_grey())
        size = 3
        wins_msg, money_msg = '```', '```'
        members = sum(not member.bot for member in ctx.message.guild.members)
        if members < size:
            size = members
        guildid = ctx.message.guild.id
        tempconn = sq.connect('database.db')
        tempc = tempconn.cursor()
        self.c.execute('''SELECT user_id, hmwins
                          FROM users
                          WHERE guild_id=?
                          ORDER BY hmwins DESC''',
                       (int(guildid),))
        tempc.execute('''SELECT user_id, hmmoney
                          FROM users
                          WHERE guild_id=?
                          ORDER BY hmmoney DESC''',
                      (int(guildid),))
        for num in range(size):
            win_values = self.c.fetchone()
            money_values = tempc.fetchone()
            win_user = self.bot.get_user(int(win_values[0])).name
            wins = win_values[1]
            money_user = self.bot.get_user(int(money_values[0])).name
            money = money_values[1]
            wins_msg += f"#{num+1} » {win_user} » {wins}\n"
            money_msg += f"#{num+1} » {money_user} » ${money}\n"
        wins_msg += '```'
        money_msg += '```'
        hmtop.add_field(name="Total Wins", value=wins_msg, inline=False)
        hmtop.add_field(name="Total Earnings", value=money_msg, inline=False)
        hmtop.set_thumbnail(url='https://i.imgur.com/wRGYezp.png')
        await ctx.send(embed=hmtop)

    @commands.command(name='guess', help='Guess a letter.',
                      aliases=['g'])
    async def guess(self, ctx, letter: str):
        guildid = ctx.message.guild.id
        user = ctx.message.author
        letter = letter.lower()
        if (guildid, user.id) in self.dict and ctx.message.channel == self.dict[(guildid, user.id)]["text_channel"]:
            await self.clear_msg(guildid, user)
            self.dict[(guildid, user.id)]["authormsg"] = ctx.message
            if len(letter) > 1:
                self.dict[(guildid, user.id)]["botmsg"] = await ctx.send('Your guess must be 1 character!')
            elif letter not in self.dict[(guildid, user.id)]["guessed"]:
                self.dict[(guildid, user.id)]["guessed"].add(letter)
                if letter in self.dict[(guildid, user.id)]["word"]:
                    self.dict[(guildid, user.id)]["botmsg"] = await ctx.send('Good guess!')
                    for i in range(len(self.dict[(guildid, user.id)]["word"])):
                        if self.dict[(guildid, user.id)]["word"][i:i+1] == letter:
                            self.dict[(guildid, user.id)]["real_word"][i] = letter
                else:
                    self.dict[(guildid, user.id)]["botmsg"] = await ctx.send('Bad guess...')
                    self.dict[(guildid, user.id)]["stage"] += 1
                    self.dict[(guildid, user.id)]["wrong"].append(letter)
            else:
                self.dict[(guildid, user.id)]["botmsg"] = await ctx.send('You have already guessed that!')
            potential_win = ''.join(self.dict[(guildid, user.id)]["real_word"])
            if potential_win == self.dict[(guildid, user.id)]["word"]:
                self.dict[(guildid, user.id)]["win"] = True
            await self.display(ctx, user)

    @guess.error
    async def guess_error(self, ctx, error):
        guildid = ctx.message.guild.id
        user = ctx.message.author
        if (guildid, user.id) not in self.dict:
            self.dict[(guildid, user.id)]["authormsg"] = ctx.message
            self.dict[(guildid, user.id)]["botmsg"] = await ctx.send('Format: -guess [letter]')
        print(error)

    @commands.command(name='answer', help='Guess the word.')
    async def answer(self, ctx, word: str):
        guildid = ctx.message.guild.id
        user = ctx.message.author
        word = word.lower()
        if (guildid, user.id) in self.dict and ctx.message.channel == self.dict[(guildid, user.id)]["text_channel"]:
            await self.clear_msg(guildid, user)
            self.dict[(guildid, user.id)]["authormsg"] = ctx.message
            if word == self.dict[(guildid, user.id)]["word"]:
                self.dict[(guildid, user.id)]["botmsg"] = await ctx.send('NICE!')
                self.dict[(guildid, user.id)]["win"] = True
            else:
                self.dict[(guildid, user.id)]["botmsg"] = await ctx.send('Bad guess...')
                self.dict[(guildid, user.id)]["stage"] += 1
            await self.display(ctx, user)

    @answer.error
    async def answer_error(self, ctx, error):
        guildid = ctx.message.guild.id
        user = ctx.message.author
        if (guildid, user.id) not in self.dict:
            self.dict[(guildid, user.id)]["authormsg"] = ctx.message
            self.dict[(guildid, user.id)]["botmsg"] = await ctx.send('Format: -answer [word]')
        print(error)

    @commands.command(name='endhm', help='End the current game.', aliases=['hmend', 'endhangman', 'hangmanend'])
    async def endhm(self, ctx):
        guildid = ctx.message.guild.id
        user = ctx.message.author
        await self.clear_msg(guildid, user)
        if (guildid, ctx.message.author.id) not in self.dict:
            await ctx.send(f'You have decided to end the game early. The word was: {self.dict[(guildid, user.id)]["word"]}.')
            self.cleanup(guildid, user)
        else:
            await ctx.send('A game is not currently in progress.')

    async def clear_msg(self, guildid, user):
        if self.dict[(guildid, user.id)]["authormsg"] or self.dict[(guildid, user.id)]["botmsg"] is not None:
            try:
                await self.dict[(guildid, user.id)]["authormsg"].delete()
            except:
                pass
            try:
                await self.dict[(guildid, user.id)]["botmsg"].delete()
            except:
                pass

    def cleanup(self, guildid, user):
        del self.dict[(guildid, user.id)]
        return

    async def display(self, ctx, user):
        guildid = ctx.guild.id
        wrd = '``` ' + ''.join([let+' ' for let in self.dict[(guildid, user.id)]["word"]]) + '```' if self.dict[(guildid, user.id)]["win"] else '``` ' + ''.join([let+' ' for let in self.dict[(guildid, user.id)]["real_word"]]) + '```'
        guessed = ''.join([let+' ' for let in self.dict[(guildid, user.id)]["guessed"]])
        self.dict[(guildid, user.id)]["stage"] = len(self.images[self.dict[(guildid, user.id)]["set"]]) - 1 if self.dict[(guildid, user.id)]["win"] else self.dict[(guildid, user.id)]["stage"]
        self.dict[(guildid, user.id)]["display"].title = 'HANGMAN'
        self.dict[(guildid, user.id)]["display"].description = wrd
        self.dict[(guildid, user.id)]["display"].set_thumbnail(url=user.avatar_url)
        self.dict[(guildid, user.id)]["display"].set_image(url=self.images[self.dict[(guildid, user.id)]["set"]][self.dict[(guildid, user.id)]["stage"]])
        self.dict[(guildid, user.id)]["display"].set_footer(text=f'» Letters guessed: {guessed}')
        if self.dict[(guildid, user.id)]["msg"] is None:
            self.dict[(guildid, user.id)]["msg"] = await ctx.send('Use `-guess <letter>` or `-answer <word>` to guess.', embed=self.dict[(guildid, user.id)]["display"])
        else:
            await self.dict[(guildid, user.id)]["msg"].edit(embed=self.dict[(guildid, user.id)]["display"])
        if self.dict[(guildid, user.id)]["win"]:
            if len(self.dict[(guildid, user.id)]["wrong"]) > 0:
                self.dict[(guildid, user.id)]["prize"] -= m.floor(self.dict[(guildid, user.id)]["prize"] * float(len(self.dict[(guildid, user.id)]["wrong"])/10))
            await self.clear_msg(guildid, user)
            self.c.execute('''SELECT money, hmwins, hmmoney
                              FROM users
                              WHERE (guild_id=? AND user_id=?)''',
                           (int(guildid), int(user.id)))
            stats = self.c.fetchone()
            self.c.execute('''UPDATE users
                              SET money=?
                              WHERE (guild_id=? AND user_id=?)''',
                           (int(self.dict[(guildid, user.id)]["prize"]) + int(stats[0]), int(guildid), int(user.id)))
            self.conn.commit()
            self.c.execute('''UPDATE users
                              SET hmwins=?
                              WHERE (guild_id=? AND user_id=?)''',
                           (1 + int(stats[1]), int(guildid), int(user.id)))
            self.conn.commit()
            self.c.execute('''UPDATE users
                              SET hmmoney=?
                              WHERE (guild_id=? AND user_id=?)''',
                           (int(self.dict[(guildid, user.id)]["prize"]) + int(stats[2]), int(guildid), int(user.id)))
            self.conn.commit()
            await ctx.send(f"Congratulations {user.name}, you guessed the word and earned `${self.dict[(guildid, user.id)]['prize']}`! You now have `${int(self.dict[(guildid, user.id)]['prize']) + int(stats[0])}`.")
            self.cleanup(guildid, user)
            return
        if self.dict[(guildid, user.id)]["stage"] == (len(self.images[self.dict[(guildid, user.id)]["set"]]) - 1):
            await self.clear_msg(guildid, user)
            await ctx.send(f"{user.name}... you lost! The word was: `{self.dict[(guildid, user.id)]['word']}`")
            self.cleanup(guildid, user)

    @commands.group(name="hst", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def hst(self, ctx, *, category: int = None):
        try:
            self.c.execute('''SELECT hm_category FROM servers WHERE guild_id=?''',
                           (int(ctx.guild.id),))
            hm_cat = self.c.fetchone()[0]
            cat = discord.utils.get(ctx.guild.categories, id=category)
            if category is None:
                if hm_cat is None:
                    return await ctx.send("You need to specify a category by ID, no category is currently set.")
                else:
                    cat = discord.utils.get(ctx.guild.categories, id=hm_cat)
                    return await ctx.send(f"The hangman category is currently set to {cat.name}.")
            if cat is not None:
                if hm_cat != category:
                    self.c.execute('''UPDATE servers
                                      SET hm_category=?
                                      WHERE guild_id=?''',
                                   (int(category), int(ctx.guild.id)))
                    self.conn.commit()
                    return await ctx.send(f"The hangman category has been set to {cat.name}.")
        except Exception:
            return await ctx.send("An invalid category ID has been provided. Please try again.")

    @hst.command(name='clear',  aliases=['remove', 'delete'])
    @commands.has_permissions(manage_guild=True)
    async def clear(self, ctx):
        self.c.execute('''UPDATE servers
                          SET hm_category=?
                          WHERE guild_id=?''',
                       (None, (ctx.guild.id)))
        self.conn.commit()
        await ctx.send("Hangman category has been cleared.")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        self.c.execute('''SELECT hm_category FROM servers WHERE guild_id=?''',
                       (int(channel.guild.id),))
        hm_cat = self.c.fetchone()[0]
        if hm_cat is not None and int(channel.id) == int(hm_cat):
            self.c.execute('''UPDATE servers
                              SET hm_category=?
                              WHERE guild_id=?''',
                           (None, (channel.guild.id)))
            self.conn.commit()
'''
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
            await channel.set_permissions(ctx.message.author, view_channel=False) '''


def setup(bot):
    bot.add_cog(Hangman(bot, "dictionary.txt"))
