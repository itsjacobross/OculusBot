import discord
import sqlite3 as sq
import random

from discord.ext import commands
from discord import Button, ButtonStyle


class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.decks = 4 * 4
        self.cards = [self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks, self.decks]
        self.deck = ["2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟", "🇯", "🇶", "🇰", "🇦"]
        self.cardsleft = sum(self.cards)
        self.dict = {}
        self.conn = sq.connect('database.db')
        self.c = self.conn.cursor()

    @commands.command(name='blackjack', help='Play a game of blackjack.',
                      aliases=['bj'])
    async def blackjack(self, ctx, buyin: str):
        guildid = ctx.message.guild.id
        if (guildid, ctx.message.author.id) not in self.dict:
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
            self.dict[(guildid, user.id)] = data
            self.c.execute('''SELECT money
                              FROM users
                              WHERE (guild_id=? AND user_id=?)''',
                           (int(guildid), int(user.id)))
            balance = self.c.fetchone()[0]
            if buyin.lower() == 'all':
                buyin = balance
            if int(buyin) > int(balance):
                await ctx.send("You do not have that much money.")
            elif int(buyin) == 0:
                await ctx.send("You cannot play for $0.")
            else:
                self.c.execute('''UPDATE users
                                  SET money=?
                                  WHERE (guild_id=? AND user_id=?)''',
                               (int(balance) - int(buyin), int(guildid), int(user.id)))
                self.conn.commit()
                self.dict[(guildid, user.id)]["prize"] = int(buyin) * 2
                self.dict[(guildid, user.id)]["buyin"] = int(buyin)
                dealer_first = self.pick_rand()
                dealer_second = self.pick_rand()
                self.dict[(guildid, user.id)]["dealer_hand_real"] += dealer_first + ' ' + dealer_second
                self.dict[(guildid, user.id)]["dealer_hand"] += dealer_second
                self.dict[(guildid, user.id)]["dealer_value"] += self.get_value(dealer_first, None, user.id, guildid) + self.get_value(dealer_second, None, user.id, guildid)
                player_first = self.pick_rand()
                player_second = self.pick_rand()
                self.dict[(guildid, user.id)]["player_hand"] += player_first + ' ' + player_second
                self.dict[(guildid, user.id)]["player_value"] += self.get_value(player_first, user, user.id, guildid) + self.get_value(player_second, user, user.id, guildid)
                await self.display(ctx, user)
        else:
            await ctx.send('You are already playing a game of Blackjack!')

    @blackjack.error
    async def blackjack_error(self, ctx, error):
        print(error)
        await ctx.send('Format: -blackjack [amount]')

    async def display(self, ctx, user):
        player = f"**{user.name}'s Hand**"
        guildid = ctx.message.guild.id
        if self.dict[(guildid, user.id)]["end"]:
            dealer_hand = self.dict[(guildid, user.id)]["dealer_hand_real"]
        else:
            dealer_hand = self.dict[(guildid, user.id)]["dealer_hand"]
        print(f'Dealer = {self.dict[(guildid, user.id)]["dealer_value"]}, {user.name} = {self.dict[(guildid, user.id)]["player_value"]}')
        self.cardsleft = sum(self.cards)
        self.dict[(guildid, user.id)]["display"].title = 'BLACKJACK'
        self.dict[(guildid, user.id)]["display"].set_thumbnail(url=user.avatar_url)
        self.dict[(guildid, user.id)]["display"].set_footer(text=f'» Number of Decks: {int(self.decks/4)}\n» Cards Remaining: {self.cardsleft}\n» ${self.dict[(guildid, user.id)]["buyin"]} bet')
        if self.dict[(guildid, user.id)]["msg"] is None:
            self.dict[(guildid, user.id)]["display"].add_field(name="**Dealer's Hand**", value=f'> {dealer_hand}', inline=False)
            self.dict[(guildid, user.id)]["display"].add_field(name=player, value=f'> {self.dict[(guildid, user.id)]["player_hand"]}')
            self.dict[(guildid, user.id)]["msg"] = await ctx.send('Use the buttons to hit or stay.', embed=self.dict[(guildid, user.id)]["display"], components=[[
            Button(label="Hit",
                   custom_id="green",
                   style=ButtonStyle.green),
            Button(label="Stay",
                   custom_id="red",
                   style=ButtonStyle.red)]])
        else:
            self.dict[(guildid, user.id)]["display"].set_field_at(index=0, name="**Dealer's Hand**", value=f'> {dealer_hand}', inline=False)
            self.dict[(guildid, user.id)]["display"].set_field_at(index=1, name=player, value=f'> {self.dict[(guildid, user.id)]["player_hand"]}')
            await self.dict[(guildid, user.id)]["msg"].edit(embed=self.dict[(guildid, user.id)]["display"])
        if self.dict[(guildid, user.id)]["end"]:
            self.c.execute('''SELECT money
                              FROM users
                              WHERE (guild_id=? AND user_id=?)''',
                           (int(guildid), int(user.id)))
            balance = self.c.fetchone()[0]
            if self.dict[(guildid, user.id)]["dealer_value"] == self.dict[(guildid, user.id)]["player_value"] and self.dict[(guildid, user.id)]["dealer_value"] <= 21:
                self.c.execute('''UPDATE users
                                  SET money=?
                                  WHERE (guild_id=? AND user_id=?)''',
                               (int(self.dict[(guildid, user.id)]["buyin"]) + int(balance), int(guildid), int(user.id)))
                self.conn.commit()
                msg = f'{user.name}, you tied with the dealer. Your original buy-in is returned to you. Your balance is `${int(balance) + int(self.dict[(guildid, user.id)]["buyin"])}`.'
            elif (self.dict[(guildid, user.id)]["dealer_value"] <= 21 and (self.dict[(guildid, user.id)]["dealer_value"] >= self.dict[(guildid, user.id)]["player_value"] or self.dict[(guildid, user.id)]["player_value"] > 21)) or (self.dict[(guildid, user.id)]["dealer_value"] > 21 and self.dict[(guildid, user.id)]["player_value"] > 21):
                msg = f'Tough luck {user.name}, the dealer outplayed you. You now have `${balance}`.'
            else:
                self.c.execute('''UPDATE users
                                  SET money=?
                                  WHERE (guild_id=? AND user_id=?)''',
                               (int(self.dict[(guildid, user.id)]["prize"]) + int(balance), int(guildid), int(user.id)))
                self.conn.commit()
                msg = f"Nice job on that W, {user.name}! You win `${self.dict[(guildid, user.id)]['prize']}`. Your new balance is `${int(balance) + int(self.dict[(guildid, user.id)]['prize'])}`."
            await ctx.send(msg)
            self.cleanup(guildid, user.id)
            return

        def check_button(i: discord.Interaction, button):
            return i.author == ctx.author and i.message == self.dict[(guildid, user.id)]["msg"]

        interaction, button = await self.bot.wait_for('button_click', check=check_button)
        if button.custom_id == "green" and interaction.author == user:
            msg = await interaction.respond(content=f"{user.name} hit.")
            await msg.delete()
            await self.hit(ctx, user, user.id, guildid)
            await self.display(ctx, user)
        elif button.custom_id == "red" and interaction.author == user:
            msg = await interaction.respond(content=f"{user.name} decided to stay.")
            await msg.delete()
            await self.hit(ctx, None, user.id, guildid)
            await self.display(ctx, user)

# LIST INDEX OUT OF RANGE OCCURS WHEN:
# PLAYER 1 STARTS GAME
# PLAYER 2 STARTS GAME
# PLAYER 1 FINISHES GAME
# PLAYER 1 STARTS GAME

    @commands.command(name='endblackjack', aliases=['endbj', 'bjend', 'blackjackend'])
    async def endbj(self, ctx):
        guildid = ctx.message.guild.id
        if (guildid, ctx.message.author.id) in self.dict:
            self.c.execute('''SELECT money
                              FROM users
                              WHERE (guild_id=? AND user_id=?)''',
                           (int(guildid), int(ctx.message.author.id)))
            balance = self.c.fetchone()[0]
            self.c.execute('''UPDATE users
                              SET money=?
                              WHERE (guild_id=? AND user_id=?)''',
                           (int(self.dict[(guildid, ctx.message.author.id)]["buyin"]) + int(balance), int(guildid), int(ctx.message.author.id)))
            self.conn.commit()
            await ctx.send(f'You have decided to fold.')
            self.cleanup(guildid, ctx.message.author.id)
        else:
            await ctx.send('You do not have an active game of Blackjack.')

    def pick_rand(self):
        self.resetdeck() if self.cardsleft < 4 else None
        index = random.choice(range(0, len(self.deck)))
        choice = self.deck[index] if self.cards[index] != 0 else self.pick_rand()
        self.cards[index] -= 1 if self.cards[index] != 0 else 0
        return choice

    def cleanup(self, guildid, userid):
        del self.dict[(guildid, userid)]
        return

    def resetdeck(self):
        self.decks = 4 * 4
        for x in range(len(self.cards)):
            self.cards[x] = self.decks
        self.cardsleft = sum(self.cards)
        return

    def get_value(self, string, player, id, guildid):
        try:
            value = int(string[0])
        except:
            if string[0] == '🇦':
                value = 11
                if player is None:
                    self.dict[(guildid, id)]["dealer_aces"] += 1
                else:
                    self.dict[(guildid, id)]["player_aces"] += 1
            else:
                value = 10
        return int(value)

    async def hit(self, ctx, player, id, guildid):
        if player is not None:
            new_card = self.pick_rand()
            self.dict[(guildid, id)]["player_hand"] += ' ' + new_card
            self.dict[(guildid, id)]["player_value"] += self.get_value(new_card, player, id, guildid)
            if self.dict[(guildid, id)]["player_value"] > 21 and self.dict[(guildid, id)]["player_aces"] > 0:
                self.dict[(guildid, id)]["player_aces"] -= 1
                self.dict[(guildid, id)]["player_value"] -= 10
            elif self.dict[(guildid, id)]["player_value"] > 21:
                await self.hit(ctx, None, id, guildid)
        else:
            if self.dict[(guildid, id)]["dealer_hand_real"] == '🇦 🇦':
                self.dict[(guildid, id)]["dealer_aces"] -= 1
                self.dict[(guildid, id)]["dealer_value"] -= 10
            while(self.dict[(guildid, id)]["dealer_value"] < 17):
                new_card = self.pick_rand()
                self.dict[(guildid, id)]["dealer_hand"] += ' ' + new_card
                self.dict[(guildid, id)]["dealer_hand_real"] += ' ' + new_card
                self.dict[(guildid, id)]["dealer_value"] += self.get_value(new_card, None, id, guildid)
                if self.dict[(guildid, id)]["dealer_value"] > 21 and self.dict[(guildid, id)]["dealer_aces"] > 0:
                    self.dict[(guildid, id)]["dealer_aces"] -= 1
                    self.dict[(guildid, id)]["dealer_value"] -= 10
            self.dict[(guildid, id)]["end"] = True


def setup(bot):
    bot.add_cog(Blackjack(bot))
