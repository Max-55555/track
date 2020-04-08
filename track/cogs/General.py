from discord.ext import commands, menus
import discord
from datetime import datetime
import timeago
import sys
import psutil

import config
import utils


class Help(commands.HelpCommand):
    def __init__(self):
        super().__init__(command_attrs={'brief': 'Take a wild guess...',
                                        'help': 'Seriously?'})

    class HelpMenu(menus.Menu):
        def __init__(self, cogs, main_embed, instance):
            super().__init__(clear_reactions_after=True)
            self.cogs = cogs
            self.main_embed = main_embed
            self.instance = instance
            for cog in cogs:
                self.add_button(menus.Button(cog.emoji, self.cog_embed))

        async def send_initial_message(self, ctx, channel):
            return await ctx.send(embed=self.main_embed)

        @menus.button('↩️')
        async def main(self, payload):
            if payload.event_type != 'REACTION_ADD':
                return
            await self.message.remove_reaction(payload.emoji, payload.member)

            await self.message.edit(embed=self.main_embed)

        @menus.button('⏹️', position=menus.Last())
        async def end(self, payload):
            self.stop()

        async def cog_embed(self, payload):
            if payload.event_type != 'REACTION_ADD':
                return
            await self.message.remove_reaction(payload.emoji, payload.member)

            for cog in self.cogs:
                if payload.emoji.name == cog.emoji:
                    await self.message.edit(embed=await self.instance.cog_embed(cog))

    async def send_bot_help(self, mapping):
        cogs = [self.context.bot.get_cog(cog) for cog in ['General', 'WoWS', 'Fun']]
        perms = discord.Permissions.text()
        perms.update(read_messages=True, manage_messages=True,
                     mention_everyone=False, send_tts_messages=False)

        embed = discord.Embed(title='Help',
                              description='A bot with WoWS related utilities and more.\n'
                                          'Contact Trackpad#1234 for issues.\n'
                                          'This bot is currently WIP.',
                              color=self.context.bot.color)
        embed.add_field(name='Command Categories',
                        value='\n'.join([f'{cog.emoji} {cog.qualified_name}' for cog in cogs]))
        embed.add_field(name='Links',
                        value=f'[Invite me here!]({discord.utils.oauth_url(self.context.bot.user.id, perms)})\n'
                              f'[Support server](https://discord.gg/dU39sjq)\n'
                              f'[Need WoWS help?](https://discord.gg/c4vK9rM)\n')
        embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/651324664496521225/651326808423137300/thumbnail.png')
        embed.set_footer(text='Use the below reactions or help <category> / help <command> to view details')

        await self.HelpMenu(cogs, embed, self).start(self.context)

    async def send_cog_help(self, cog):
        await self.context.send(embed=await self.cog_embed(cog))

    async def cog_embed(self, cog):
        cogs = [self.context.bot.get_cog(cog) for cog in ['General']]
        if cog.qualified_name in cogs:
            return

        def descriptor(command):
            string = f'`{command.name}` - {command.short_doc}'
            if isinstance(command, commands.Group):
                string += f'\n┗ {", ".join(f"`{sub}`" for sub in command.all_commands)}'
            return string

        embed = discord.Embed(title=f'Help - {cog.qualified_name}',
                              description=cog.description,
                              color=self.context.bot.color)
        embed.add_field(name='Available Commands',
                        value='\n'.join([descriptor(command) for command in cog.get_commands() if not command.hidden]))
        embed.set_footer(text='Use help <command> to view the usage of that command.')

        return embed

    async def send_group_help(self, group):
        embed = discord.Embed(title=f'Help - {group.name}',
                              description=group.help,
                              color=self.context.bot.color)
        if group.aliases:
            embed.add_field(name='Aliases',
                            value=', '.join(f'`{alias}`' for alias in group.aliases),
                            inline=False)
        for command in group.commands:
            embed.add_field(name=command.name,
                            value=f'{command.help} ```{utils.get_signature(command)}```',
                            inline=False)
        embed.set_footer(text='<REQUIRED argument> | [OPTIONAL argument] | (Do not type these symbols!)')

        await self.context.send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(title=f'Help - {command.name}',
                              description=command.help,
                              color=self.context.bot.color)
        if command.aliases:
            embed.add_field(name='Aliases',
                            value=', '.join(f'`{alias}`' for alias in command.aliases),
                            inline=False)
        embed.add_field(name='Usage',
                        value=f'```{utils.get_signature(command)}```')
        embed.set_footer(text='<REQUIRED argument> | [OPTIONAL argument] | (Do not type these symbols!)')
        await self.context.send(embed=embed)


class General(commands.Cog):
    """
    General commands for the bot.
    """

    def __init__(self, bot):
        self.bot = bot
        self.emoji = '📔'

        self._original_help_command = bot.help_command
        bot.help_command = Help()
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self._original_help_command

    @commands.command(aliases=['join'], brief='Gets bot\'s invite link.')
    async def invite(self, ctx):
        """
        Gets an invite link for the bot.
        """
        perms = discord.Permissions.text()
        perms.update(read_messages=True, manage_messages=True,
                     mention_everyone=False, send_tts_messages=False)
        await ctx.send(f'Invite me here:\n<{discord.utils.oauth_url(self.bot.user.id, perms)}>')

    @commands.command(aliases=['server'], brief='Gets support server\'s invite link.')
    async def support(self, ctx):
        """
        Gets an invite link to the support server.
        """
        await ctx.send('Support server:\nhttps://discord.gg/dU39sjq')

    @commands.command(aliases=['latency'], brief='Pong?')
    async def ping(self, ctx):
        """
        Pong?
        """
        start = datetime.now()
        await ctx.trigger_typing()
        end = datetime.now()
        await ctx.send(f'Ping: `{(end - start).total_seconds() * 1000:.2f}ms`.')

    @commands.command(brief='Displays bot\'s uptime.')
    async def uptime(self, ctx):
        """
        Shows you the last time the bot was launched, due to scheduled reboot or an update (and hopefully not a crash).
        """
        await ctx.send(f'Online since {self.bot.uptime.strftime("%m/%d/%Y %H:%M UTC")} '
                       f'(~{timeago.format(self.bot.uptime, datetime.utcnow())})')

    @commands.command(aliases=['suggest'], brief='Send feedback (suggestions & feature requests).')
    @commands.cooldown(rate=1, per=60, type=commands.cooldowns.BucketType.user)
    async def feedback(self, ctx, *, message):
        """
        Send in feedback here! Attachments accepted, but remember to attach them all.
        """
        channel = self.bot.get_channel(config.feedback_channel)  # feedback chanel in support server

        embed = discord.Embed(title='New Feedback!',
                              description=message,
                              color=self.bot.color)
        embed.add_field(name='Author',
                        value=ctx.author.mention)
        embed.add_field(name='Server',
                        value=ctx.guild.name)
        if ctx.message.attachments:
            embed.add_field(name='Attachments',
                            value='\n'.join(f'[{file.filename}]({file.url})' for file in ctx.message.attachments),
                            inline=False)
        embed.set_footer(text='Vote on this submissions using the reactions so I can determine what to focus on!')

        message = await channel.send(embed=embed)
        await message.add_reaction('<:upvote:651325140663140362>')
        await message.add_reaction('<:downvote:651325233105600544>')
        await ctx.send('Thank you for your submission! '
                       'If you haven\'t already, consider joining the support server with `support`.')

    @commands.command(brief='Answers to some common questions.')
    async def faq(self, ctx):
        """
        Lists frequently asked questions and their responses.
        """
        embed = discord.Embed(title='FAQ',
                              color=self.bot.color)
        entries = {'How do I add this bot to my server?':
                       'Use `invite` or click the link in `help` (you must have Manage Server permissions).',
                   'Hey, can you add (some feature)?':
                       'Use `suggest`.',
                   'None of the commands are working!':
                       'The bot may be missing permissions or you may have been automatically blacklisted for spam. '
                       'If the problem persists, report it.',
                   'What character is that in the profile picture?':
                       '[Shiro from Sewayaki Kitsune no Senko-san!](https://myanimelist.net/character/167062/Shiro)'}
        for name, value in entries.items():
            embed.add_field(name=name, value=value, inline=False)
        embed.set_footer(text='Have other questions? Join the support discord or PM me @Trackpad#1234.')

        await ctx.send(embed=embed)

    @commands.command(aliases=['about', 'details'], brief='Displays extra information about the bot.')
    async def info(self, ctx):
        """
        Displays specifics of the bot.
        """
        python = sys.version_info

        start = datetime.now()
        await ctx.trigger_typing()
        end = datetime.now()

        process = psutil.Process()

        embed = discord.Embed(title='Info',
                              color=self.bot.color)
        embed.add_field(name='Latest Changelog',
                        value='Restructured the project.',
                        inline=False)
        embed.add_field(name='Creator',
                        value='\n'.join(self.bot.get_user(owner).mention for owner in self.bot.owner_ids))
        embed.add_field(name='Created on',
                        value=f'{self.bot.created_on.strftime("%m/%d/%Y")}\n'
                              f'(~{timeago.format(self.bot.created_on, datetime.utcnow())})')
        embed.add_field(name='Made With',
                        value=f'[Python {python.major}.{python.minor}.{python.micro}](https://www.python.org/)\n'
                              f'[discord.py {discord.__version__}](https://discordpy.readthedocs.io/en/latest/)')
        embed.add_field(name='Status',
                        value=f'Ping: {(end - start).total_seconds() * 1000:.2f}ms\n'
                              f'CPU: {process.cpu_percent()}%\n'
                              f'RAM: {process.memory_info().rss / 1048576:.2f}MB')  # bits to bytes
        embed.add_field(name='Uptime',
                        value='Online since:\n'
                              f'{self.bot.uptime.strftime("%m/%d/%Y %H:%M UTC")}\n'
                              f'(~{timeago.format(self.bot.uptime, datetime.utcnow())})')
        embed.add_field(name='Statistics',
                        value=f'Commands Run: {1003}\n'
                              f'Guilds: {len(list(self.bot.guilds))}\n'
                              f'Users: {len(list(self.bot.get_all_members()))} '
                              f'(Unique: {len(set(self.bot.get_all_members()))})')
        embed.add_field(name='Acknowledgements',
                        value='<@113104128783159296> - Answering a lot of questions I had, couldn\'t have done it with you!\n'
                              '`[RKN]` - Testing! thanks guys :)',
                        inline=False)

        await ctx.send(embed=embed)

    # @commands.command()
    # @commands.is_owner()
    # async def leave_guild(self, ctx, guild: int):
    #     await self.bot.get_guild(guild).leave()
    #     await ctx.send('Done.')


def setup(bot):
    bot.add_cog(General(bot))
