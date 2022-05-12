import os
import discord
import sqlite3 as sq

from dotenv import load_dotenv
from discord.ext import commands

conn = sq.connect('database.db')
c = conn.cursor()

intents = discord.Intents.all()
intents.members = True
intents.guilds = True

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

INITIAL_EXTENSIONS = [
    'cogs.special',
    'cogs.help',
    'cogs.cst',
    'cogs.profile',
    'cogs.mod',
    'cogs.gamble',
    'cogs.blackjack',
    'cogs.hangman',
    'cogs.leaderboard'
]


class OculusBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='-',
                         activity=discord.Game(name="-help"),
                         status=discord.Status.dnd,
                         intents=intents,
                         case_insensitive=True,
                         command_attrs=dict(hidden=True)
                         )
        self.owner_id = 173660107689689089
        self.token = TOKEN
        self.remove_command('help')

        for extension in INITIAL_EXTENSIONS:
            try:
                self.load_extension(extension)
                print(f'Successfully loaded {extension}\n')
            except Exception as e:
                print(f'Failed to load extension {extension}\n{type(e).__name__}: {e}')

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord!')
        c.execute(''' CREATE TABLE IF NOT EXISTS servers (
                        guild_id INTEGER UNIQUE,
                        server_name text,
                        bot_alias text,
                        cst_category INTEGER,
                        hm_category INTEGER,
                        chatlogs_chan INTEGER,
                        modlogs_chan INTEGER)''')

        c.execute('''CREATE TABLE IF NOT EXISTS users
                  (user_id INTEGER, guild_id INTEGER, money INTEGER, hmwins INTEGER, hmmoney INTEGER)''')
#        c.execute('''ALTER TABLE servers
#                        ADD COLUMN chatlogs_chan INTEGER''')
#
#   This can be edited when a new column is needed during development.
#
        for guild in self.guilds:
            c.execute('''INSERT OR IGNORE INTO servers
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (int(guild.id), None, None, None, None, None, None))
            conn.commit()
            c.execute('''UPDATE servers
                         SET server_name=?
                         WHERE guild_id=?''',
                      (guild.name, int(guild.id)))
            conn.commit()
            for user in guild.members:
                if not user.bot:
                    c.execute('''INSERT OR IGNORE INTO users
                                 VALUES (?, ?, ?, ?, ?)''',
                              (int(user.id), int(guild.id), 500, 0, 0))
                    conn.commit()

    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)

    async def on_member_update(self, before, after):
        if after.id == self.user.id and before.nick != after.nick:
            c.execute('''UPDATE servers
                         SET bot_alias=?
                         WHERE guild_id=?''',
                      (after.nick, int(after.guild.id)))
            conn.commit()

    async def on_guild_update(self, before, after):
        if before.name != after.name:
            c.execute('''UPDATE servers
                         SET server_name=?
                         WHERE guild_id=?''',
                      (after.name, int(after.id)))
            conn.commit()

    async def close(self):
        await super().close()

    def run(self):
        super().run(self.token)


oculusbot = OculusBot()
oculusbot.run()
