import discord
import spotipy
import json
import spotipy.util as util

from discord.ext import commands
from discord import app_commands

scope = ['user-library-read', 'user-library-modify',
         'user-modify-playback-state']

class Spotify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Users send access token from authetication link to grant bot permissions
    @app_commands.command(name='link', description='Send your Spotify username')
    async def link(self, interaction: discord.Interaction, username: str):
        user = interaction.user

        with open('credentials.json') as f:
            creds = json.load(f)
        creds[user.id] = username
        with open('credentials.json', 'w') as f:
            json.dump(creds, f)

        await interaction.response.send_message(f"Associating your Discord account with {username}. If username is typed incorrectly, bot functions will not work properly.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Spotify(bot))
