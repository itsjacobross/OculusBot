import discord
import sqlite3 as sq

from discord.ext import commands


class ChannelSpecificText(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sq.connect('database.db')
        self.c = self.conn.cursor()

    @commands.group(name="cst", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def cst(self, ctx, *, category: int = None):
        try:
            self.c.execute('''SELECT cst_category FROM servers WHERE guild_id=?''',
                           (int(ctx.guild.id),))
            cst_cat = self.c.fetchone()[0]
            cat = discord.utils.get(ctx.guild.categories, id=category)
            if category is None:
                if cst_cat is None:
                    return await ctx.send("You need to specify a category by ID, no category is currently set.")
                else:
                    cat = discord.utils.get(ctx.guild.categories, id=cst_cat)
                    return await ctx.send(f"The channel specific text category is currently set to {cat.name}.")
            if cat is not None:
                if cst_cat != category:
                    self.c.execute('''UPDATE servers
                                      SET cst_category=?
                                      WHERE guild_id=?''',
                                   (int(category), int(ctx.guild.id)))
                    self.conn.commit()
                    return await ctx.send(f"The channel specific text category has been set to {cat.name}.")
        except Exception:
            return await ctx.send("An invalid category ID has been provided. Please try again.")

    @cst.command(name='clear',  aliases=['remove', 'delete'])
    @commands.has_permissions(manage_guild=True)
    async def clear(self, ctx):
        self.c.execute('''UPDATE servers
                          SET cst_category=?
                          WHERE guild_id=?''',
                       (None, (ctx.guild.id)))
        self.conn.commit()
        await ctx.send("Channel specific text category has been cleared.")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        self.c.execute('''SELECT cst_category FROM servers WHERE guild_id=?''',
                       (int(channel.guild.id),))
        cst_cat = self.c.fetchone()[0]
        if cst_cat is not None and int(channel.id) == int(cst_cat):
            self.c.execute('''UPDATE servers
                              SET cst_category=?
                              WHERE guild_id=?''',
                           (None, (channel.guild.id)))
            self.conn.commit()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        self.c.execute('''SELECT cst_category FROM servers WHERE guild_id=?''',
                       (int(member.guild.id),))
        cst_cat = self.c.fetchone()[0]
        if cst_cat is not None:
            # When the user changes channels
            if before.channel != after.channel:
                # If the user was previously in another voice channel, note the VC ID
                if before.channel is not None:
                    # prev_chan_id = before.channel.id
                    prev_chan_name = (before.channel.name).replace(' ','-').lower()
                # If the user is joining another voice channel, note the VC ID
                if after.channel is not None:
                    # curr_chan = after.channel.id
                    curr_chan_name = after.channel.name.replace(' ','-').lower()
                else:
                    curr_chan_name = None
                # Note all of the existing text channels in Channel Specific Text category
                text_channel_list = []
                cat = discord.utils.get(member.guild.categories, id=int(cst_cat))
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
                    text_chan = discord.utils.get(member.guild.text_channels, name=curr_chan_name, category=cat)
                    await text_chan.set_permissions(member, view_channel=True)
                else:
                    pass


async def setup(bot):
    await bot.add_cog(ChannelSpecificText(bot))
