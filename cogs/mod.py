import discord
import sqlite3 as sq

from discord.ext import commands


class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sq.connect('database.db')
        self.c = self.conn.cursor()

    @commands.group(name="chatlog", invoke_without_command=True, aliases=['chatlogs'])
    @commands.has_permissions(manage_guild=True)
    async def chatlog(self, ctx, *, channel: discord.TextChannel = None):
        try:
            self.c.execute('''SELECT chatlogs_chan FROM servers WHERE guild_id=?''',
                           (int(ctx.guild.id),))
            chan = self.c.fetchone()[0]
            if channel is None:
                if chan is None:
                    return await ctx.send("You need to specify a channel by mention, no channel is currently set.")
                else:
                    return await ctx.send(f"The chat log channel is currently set to {chan.name}.")
            if channel is not None:
                if chan != channel:
                    self.c.execute('''UPDATE servers
                                      SET chatlogs_chan=?
                                      WHERE guild_id=?''',
                                   (int(channel.id), int(ctx.guild.id)))
                    self.conn.commit()
                    return await ctx.send(f"The chat log has been set to {channel.name}.")
        except Exception:
            return await ctx.send("An invalid channel ID has been provided. Please try again.")

    @chatlog.command(name='clear',  aliases=['remove', 'delete'])
    @commands.has_permissions(manage_guild=True)
    async def clear(self, ctx):
        self.c.execute('''UPDATE servers
                          SET chatlogs_chan=?
                          WHERE guild_id=?''',
                       (None, (ctx.guild.id)))
        self.conn.commit()
        await ctx.send("Chat log channel has been cleared.")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        self.c.execute('''SELECT chatlogs_chan FROM servers WHERE guild_id=?''',
                       (int(channel.guild.id),))
        chan = self.c.fetchone()[0]
        if chan is not None and int(channel.id) == int(chan):
            self.c.execute('''UPDATE servers
                              SET chatlogs_chan=?
                              WHERE guild_id=?''',
                           (None, (channel.guild.id)))
            self.conn.commit()

    @commands.Cog.listener()
    async def on_message(self, message):
        chan = message.channel
        user = message.author
        if not user.bot and not message.content.startswith("-"):
            self.c.execute('''SELECT chatlogs_chan FROM servers WHERE guild_id=?''',
                           (int(message.guild.id),))
            channel = self.c.fetchone()[0]
            logs_chan = self.bot.get_channel(channel)
            if channel is not None and int(chan.id) != int(channel):
                msgtosend = f"[{chan.name}] {user.name}: {message.content}"
                # emb = message.embeds[0] if len(message.embeds) > 0 else None
                attach = await message.attachments[0].to_file() if len(message.attachments) > 0 else None
                await logs_chan.send(msgtosend, file=attach)


def setup(bot):
    bot.add_cog(Mod(bot))
