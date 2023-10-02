import os
import re
import discord
import sqlite3 as sq
import spotipy
import json
import urlexpander

from dotenv import load_dotenv
from discord.ext import commands

# Discord ID: Spotify username
spotify_dict = {}
with open('credentials.json') as f:
    spotify_dict = json.load(f)

conn = sq.connect('database.db')
c = conn.cursor()

intents = discord.Intents.all()
intents.members = True
intents.guilds = True

load_dotenv()
OCULUS_TOKEN = os.getenv('OCULUS_DISCORD_TOKEN')

OCULUS_SPOTIPY_CLIENT_ID = os.getenv('OCULUS_SPOTIPY_CLIENT_ID')
OCULUS_SPOTIPY_CLIENT_SECRET = os.getenv('OCULUS_SPOTIPY_CLIENT_SECRET')
OCULUS_SPOTIPY_REDIRECT_URI = os.getenv('OCULUS_SPOTIPY_REDIRECT_URI')
OCULUS_SPOTIFY_ID = os.getenv('OCULUS_SPOTIFY_ID')

bangaplaylist = '5wkZfEnfzlDU3qF5fIF7yG'
bangachannel = 680011474856574991

PAUSERNAME = os.getenv('PAUSERNAME')
PAPASSWORD = os.getenv('PAPASSWORD')
PATOKEN = os.getenv('PATOKEN')

scope = ['user-library-read',
         'user-library-modify',
         'user-modify-playback-state',
         'user-top-read',
         'user-read-private',
         'user-read-email',
         'playlist-modify-public'
         ]

cache_path = './caches/'

page_url = 'https://itsjacobross.github.io/'
cache_url = 'https://www.pythonanywhere.com/api/v0/user/discspotq/files/path/home/discspotq/tokens/'

INITIAL_EXTENSIONS = [
    'cogs.special',
    'cogs.help',
    'cogs.cst',
    'cogs.profile',
    'cogs.mod',
    'cogs.gamble',
    'cogs.blackjack',
    'cogs.hangman',
    'cogs.leaderboard',
    'cogs.spotify'
]


async def generate_playlist_tracks(sp):
    global playlist_tracks
    results = sp.playlist_tracks(playlist_id=bangaplaylist, limit=100)
    tracks = results["items"]
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    playlist_tracks = [track["track"]
                       ["uri"].split(":")[-1] for track in tracks]

async def check_if_in_playlist(sp, track_uri):
    return True if track_uri in playlist_tracks else False

async def add_to_playlist(sp, track_uri):
    if isinstance(track_uri, str):
        sp.user_playlist_add_tracks(user=OCULUS_SPOTIFY_ID,
                                    playlist_id=bangaplaylist,
                                    tracks=[track_uri])
        playlist_tracks.append(track_uri)
    else:
        sp.user_playlist_add_tracks(user=OCULUS_SPOTIFY_ID,
                                    playlist_id=bangaplaylist,
                                    tracks=track_uri)
        playlist_tracks.extend(track_uri)

def add_message(is_in_playlist):
    msg = "added bluh" if not is_in_playlist else "already here dumbass"
    return msg

async def remove_from_playlist(sp, track_uri):
    if isinstance(track_uri, str):
        sp.user_playlist_remove_all_occurrences_of_tracks(user=OCULUS_SPOTIFY_ID,
                                                          playlist_id=bangaplaylist,
                                                          tracks=[track_uri])
        playlist_tracks.remove(track_uri)
    else:
        sp.user_playlist_remove_all_occurrences_of_tracks(user=OCULUS_SPOTIFY_ID,
                                                          playlist_id=bangaplaylist,
                                                          tracks=track_uri)
        for tracks in track_uri:
            playlist_tracks.remove(tracks)

def remove_message(sp, uri, is_in_playlist):
    name = sp.track(uri)['name']
    msg = f"{name}? that shit weak. gone." if is_in_playlist else "song aint even there"
    return msg

def get_cached_tokens():
    response = requests.get(cache_url, headers={'Authorization': f'Token {PATOKEN}'})
    if response.status_code == 200:
        for file in response.json():
            if not os.path.isfile('./caches/'+file):
                url = response.json()[file]["url"]
                contents = requests.get(url, headers={'Authorization': f'Token {PATOKEN}'}).text
                with open(cache_path+file, 'w') as f:
                    f.write(contents)
            requests.delete(cache_url+str(file), headers={'Authorization': f'Token {PATOKEN}'})


class SpotifyButtons(discord.ui.View):
    def __init__(self, message_id, link):
        super().__init__(timeout=None)

        self.message_id = str(message_id)
        self.link = link

    @discord.ui.button(label='Add to Queue', style=discord.ButtonStyle.blurple, custom_id='spotify-queue')
    async def addtoqueue(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        with open('credentials.json') as f:
            spotify_dict = json.load(f)
        if str(user_id) in spotify_dict:
            spotify_username = spotify_dict[str(user_id)]
            cache_file = cache_path + '.cache-' + str(spotify_username)
            if not os.path.isfile(cache_file):
                get_cached_tokens()
            if not os.path.isfile(cache_file):
                await interaction.response.send_message(content=f'Please authorize via this link and try again. Then paste your Spotify username via /link. Use the username that the website gives you: {page_url}', ephemeral=True, delete_after=300)
                return
            spot_id = spotify_dict[str(user_id)]
            sp_oauth = spotipy.oauth2.SpotifyOAuth(client_id=OCULUS_SPOTIPY_CLIENT_ID,
                                                   client_secret=OCULUS_SPOTIPY_CLIENT_SECRET,
                                                   redirect_uri=OCULUS_SPOTIPY_REDIRECT_URI,
                                                   scope=scope,
                                                   cache_path=cache_file,
                                                   username=spot_id,
                                                   open_browser=False)
            with open(cache_file) as cache:
                cache_info = json.load(cache)
            refresh_token = cache_info['refresh_token']
            sp_oauth.refresh_access_token(refresh_token)
            sp = spotipy.Spotify(auth_manager=sp_oauth)
            await interaction.response.send_message(content='Adding to your queue...', ephemeral=True, delete_after=30)
            if "track" in self.link:
                sp.add_to_queue(self.link)
            elif "album" in self.link:
                results = sp.album_tracks(self.link)
                album = results['items']
                for song in album:
                    sp.add_to_queue(song['id'])
            await interaction.edit_original_response(content='Added to your queue!')
        else:
            await interaction.response.send_message(content=f'Authorize then link your Spotify username via /link. Use the name given to you by the authorization link: {page_url}', ephemeral=True, delete_after=300)

    @discord.ui.button(label='Add to Liked Songs', style=discord.ButtonStyle.green, custom_id='spotify-liked')
    async def addtoliked(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        with open('credentials.json') as f:
            spotify_dict = json.load(f)
        if str(user_id) in spotify_dict:
            spotify_username = spotify_dict[str(user_id)]
            cache_file = cache_path + '.cache-' + str(spotify_username)
            if not os.path.isfile(cache_file):
                get_cached_tokens()
            if not os.path.isfile(cache_file):
                await interaction.response.send_message(content=f'Please authorize via this link and try again. Then paste your Spotify username via /link. Use the username that the website gives you: {page_url}', ephemeral=True, delete_after=300)
                return
            spot_id = spotify_dict[str(user_id)]
            sp_oauth = spotipy.oauth2.SpotifyOAuth(client_id=OCULUS_SPOTIPY_CLIENT_ID,
                                                   client_secret=OCULUS_SPOTIPY_CLIENT_SECRET,
                                                   redirect_uri=OCULUS_SPOTIPY_REDIRECT_URI,
                                                   scope=scope,
                                                   cache_path=cache_file,
                                                   username=spot_id,
                                                   open_browser=False)
            with open(cache_file) as cache:
                cache_info = json.load(cache)
            refresh_token = cache_info['refresh_token']
            sp_oauth.refresh_access_token(refresh_token)
            sp = spotipy.Spotify(auth_manager=sp_oauth)
            await interaction.response.send_message(content='Adding to your queue...', ephemeral=True, delete_after=30)
            if "track" in self.link:
                sp.current_user_saved_tracks_add([self.link])
            elif "album" in self.link:
                results = sp.album_tracks(self.link)
                album = results['items']
                songs = []
                for song in album:
                    songs.append(song['id'])
                sp.current_user_saved_tracks_add(songs)
            await interaction.edit_original_response(content='Added to your liked songs!')
        else:
            await interaction.response.send_message(content=f'Authorize then link your Spotify username via /link. Use the name given to you by the authorization link: {page_url}', ephemeral=True, delete_after=300)


class OculusBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='-',
                         activity=discord.Game(name="/help"),
                         status=discord.Status.dnd,
                         intents=intents,
                         case_insensitive=True,
                         command_attrs=dict(hidden=True)
                         )
        self.owner_id = 173660107689689089
        self.token = OCULUS_TOKEN
        self.remove_command('help')

    async def load(self):
        for extension in INITIAL_EXTENSIONS:
            try:
                await self.load_extension(extension)
                print(f'Successfully loaded {extension}\n')
            except Exception as e:
                print(
                    f'Failed to load extension {extension}\n{type(e).__name__}: {e}')

    async def on_ready(self):
        await self.load()

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

            if not os.path.isfile(str(guild.id)+'-messages.json'):
                f = open(str(guild.id)+'-messages.json', 'w')
                f.write('{}')
                f.close()

        cache_file = cache_path + '.cache-' + str(OCULUS_SPOTIFY_ID)
        if not os.path.isfile(cache_file):
            get_cached_tokens()

        sp_oauth = spotipy.oauth2.SpotifyOAuth(client_id=OCULUS_SPOTIPY_CLIENT_ID,
                                                client_secret=OCULUS_SPOTIPY_CLIENT_SECRET,
                                                redirect_uri=OCULUS_SPOTIPY_REDIRECT_URI,
                                                scope=scope,
                                                cache_path=cache_file,
                                                username=OCULUS_SPOTIFY_ID,
                                                open_browser=False)
        with open(cache_file) as cache:
            cache_info = json.load(cache)
        refresh_token = cache_info['refresh_token']
        sp_oauth.refresh_access_token(refresh_token)
        spowner = spotipy.Spotify(auth_manager=sp_oauth)

        await generate_playlist_tracks(spowner)

        print(f'{self.user.name} has connected to Discord!')

    async def on_message(self, message):
        if message.author.bot:
            return

        spotify_link = None
        guild = str(message.guild.id)

        if "spotify.link" in message.content:
            spotify_link = re.search("https://spotify.link/[a-zA-Z0-9]*", message.content).group(0)
            spotify_link = urlexpander.expand(spotify_link)
        elif "open.spotify.com" in message.content:
            spotify_link = re.search("https://open.spotify.com/(track|album)/[a-zA-Z0-9\?\=]*", message.content).group(0)

        uri = spotify_link.split("/")[-1].split("?")[0] if spotify_link else None
        uri_type = spotify_link.split("/")[-2] if spotify_link else None

        # Handle spotify messages

        if uri:
            # Handle banga alert
            if message.channel.id == bangachannel:
                cache_file = cache_path + '.cache-' + str(OCULUS_SPOTIFY_ID)
                if not os.path.isfile(cache_file):
                    get_cached_tokens()

                sp_oauth = spotipy.oauth2.SpotifyOAuth(client_id=OCULUS_SPOTIPY_CLIENT_ID,
                                                    client_secret=OCULUS_SPOTIPY_CLIENT_SECRET,
                                                    redirect_uri=OCULUS_SPOTIPY_REDIRECT_URI,
                                                    scope=scope,
                                                    cache_path=cache_file,
                                                    username=OCULUS_SPOTIFY_ID,
                                                    open_browser=False)
                with open(cache_file) as cache:
                    cache_info = json.load(cache)
                refresh_token = cache_info['refresh_token']
                sp_oauth.refresh_access_token(refresh_token)
                sp = spotipy.Spotify(auth_manager=sp_oauth)

                if uri_type == "track":
                    is_in_playlist = await check_if_in_playlist(sp, uri)
                    msg = add_message(is_in_playlist)
                    if not is_in_playlist:
                        await add_to_playlist(sp, uri)
                    await message.reply(msg, mention_author=False)
                    await message.add_reaction('❌')

                elif uri_type == "album":
                    tracks = sp.album_tracks(uri)
                    new_songs = []
                    msg = "all songs already in playlist dumbass"

                    for track in tracks['items']:
                        track_uri = track["uri"].split(":")[-1]
                        is_in_playlist = await check_if_in_playlist(sp, track_uri)
                        if not is_in_playlist:
                            new_songs.append(track_uri)

                    if len(new_songs) > 0:
                        msg = "added all the new songs brotha"
                        await add_to_playlist(sp, new_songs)

                    await message.reply(msg, mention_author=False)
                    await message.add_reaction('❌')

            # Add buttons
            
            cache_file = cache_path + '.cache-' + str(OCULUS_SPOTIFY_ID)
            if not os.path.isfile(cache_file):
                get_cached_tokens()

            sp_oauth = spotipy.oauth2.SpotifyOAuth(client_id=OCULUS_SPOTIPY_CLIENT_ID,
                                                   client_secret=OCULUS_SPOTIPY_CLIENT_SECRET,
                                                   redirect_uri=OCULUS_SPOTIPY_REDIRECT_URI,
                                                   scope=scope,
                                                   cache_path=cache_file,
                                                   username=OCULUS_SPOTIFY_ID,
                                                   open_browser=False)
            with open(cache_file) as cache:
                cache_info = json.load(cache)
            refresh_token = cache_info['refresh_token']
            sp_oauth.refresh_access_token(refresh_token)
            spowner = spotipy.Spotify(auth_manager=sp_oauth)

            try:
                info = spowner.track(uri)
            except:
                info = spowner.album(uri)

            name = info['name']
            artist = info['artists'][0]['name']

            buttons = SpotifyButtons(message.id, spotify_link)

            reply = await message.reply(f'`{name} by {artist}`', mention_author=False, view=buttons)

            with open(guild+'-messages.json') as f:
                messages = json.load(f)
            messages[message.id] = [reply.id, spotify_link]
            with open(guild+'-messages.json', 'w') as f:
                json.dump(messages, f)

            await buttons.wait()
        await self.process_commands(message)

    async def on_raw_message_delete(self, payload):
        msgid = str(payload.message_id)
        channel = self.get_channel(payload.channel_id)
        guild = str(channel.guild.id)
        with open(guild+'-messages.json') as f:
            messages = json.load(f)
        if msgid in messages:
            reply = await channel.fetch_message(messages[msgid][0])
            await reply.delete()
            del messages[msgid]
            with open(guild+'-messages.json', 'w') as f:
                json.dump(messages, f)

    async def on_raw_reaction_add(self, payload):
        chan = self.get_channel(payload.channel_id)
        message = await chan.fetch_message(payload.message_id)
        reactions = message.reactions
        count = 0
        for reaction in reactions:
            if reaction.emoji == "❌":
                count = reaction.count
                break
        if payload.channel_id == bangachannel and payload.emoji.name == "❌" and count > 3:
            if "open.spotify.com" in message.content:
                cache_file = cache_path + '.cache-' + str(OCULUS_SPOTIFY_ID)
                if not os.path.isfile(cache_file):
                    get_cached_tokens()

                sp_oauth = spotipy.oauth2.SpotifyOAuth(client_id=OCULUS_SPOTIPY_CLIENT_ID,
                                                    client_secret=OCULUS_SPOTIPY_CLIENT_SECRET,
                                                    redirect_uri=OCULUS_SPOTIPY_REDIRECT_URI,
                                                    scope=scope,
                                                    cache_path=cache_file,
                                                    username=OCULUS_SPOTIFY_ID,
                                                    open_browser=False)
                with open(cache_file) as cache:
                    cache_info = json.load(cache)
                refresh_token = cache_info['refresh_token']
                sp_oauth.refresh_access_token(refresh_token)
                sp = spotipy.Spotify(auth_manager=sp_oauth)

                uri = message.content.split("/")[-1].split("?")[0]

                if "track" in message.content:
                    is_in_playlist = await check_if_in_playlist(sp, uri)
                    msg = remove_message(sp, uri, is_in_playlist)
                    if is_in_playlist:
                        await remove_from_playlist(sp, uri)
                    await message.channel.send(msg)
                    await message.delete()

                elif "album" in message.content:
                    tracks = sp.album_tracks(uri)
                    songs_to_remove = []
                    msg = "them songs not there"

                    for track in tracks['items']:
                        track_uri = track["uri"].split(":")[-1]
                        is_in_playlist = await check_if_in_playlist(sp, track_uri)
                        if is_in_playlist:
                            songs_to_remove.append(track_uri)

                    if len(songs_to_remove) > 0:
                        msg = f"took out all the shit from {sp.album(uri)['name']}"
                        await remove_from_playlist(sp, songs_to_remove)

                    await message.channel.send(msg)
                    await message.delete()

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

    async def on_guild_join(self, guild):
        if not os.path.isfile(str(guild.id)+'-messages.json'):
                f = open(str(guild.id)+'-messages.json', 'w')
                f.write('{}')
                f.close()

    async def setup_hook(self):
        for file in os.listdir():
            if re.match(r'^\d+-messages\.json', file):
                with open(file) as f:
                    messages = json.load(f)

                for message_id in messages:
                    view = SpotifyButtons(message_id, messages[message_id][1])
                    self.add_view(view, message_id=messages[message_id][0])

    async def close(self):
        await super().close()

    def run(self):
        super().run(self.token)


oculusbot = OculusBot()
oculusbot.run()
