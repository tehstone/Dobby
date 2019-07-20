import asyncio
import copy
import datetime
import errno
import functools
import gettext
import heapq
import io
import itertools
import json
import os
import pickle
import random
import re
import sys
import tempfile
import textwrap
import time
import traceback

from contextlib import redirect_stdout
from io import BytesIO
from operator import itemgetter
from time import strftime

import aiohttp
import dateparser
from dateutil import tz
from dateutil.relativedelta import relativedelta

import discord
from discord.ext import commands

from dobby.exts.db.dobbydb import *
DobbyDB.start('data/dobby.db')


from dobby import checks, configuration, utils, constants
from dobby.bot import DobbyBot
from dobby.errors import custom_error_handling
from dobby.logs import init_loggers

logger = init_loggers()
_ = gettext.gettext

def _get_prefix(bot, message):
    guild = message.guild
    try:
        prefix = bot.guild_dict[guild.id]['configure_dict']['settings']['prefix']
    except (KeyError, AttributeError):
        prefix = None
    if not prefix:
        prefix = bot.config['default_prefix']
    return commands.when_mentioned_or(prefix)(bot, message)

Dobby = DobbyBot(
    command_prefix=_get_prefix, case_insensitive=True,
    activity=discord.Game(name="Wizards Unite"))

Dobby.success_react = '✅'
Dobby.failed_react = '❌'
Dobby.empty_str = '\u200b'

custom_error_handling(Dobby, logger)

def _load_data(bot):
    try:
        with open(os.path.join('data', 'serverdict'), 'rb') as fd:
            bot.guild_dict = pickle.load(fd)
        logger.info('Serverdict Loaded Successfully')
    except OSError:
        logger.info('Serverdict Not Found - Looking for Backup')
        try:
            with open(os.path.join('data', 'serverdict_backup'), 'rb') as fd:
                bot.guild_dict = pickle.load(fd)
            logger.info('Serverdict Backup Loaded Successfully')
        except OSError:
            logger.info('Serverdict Backup Not Found - Creating New Serverdict')
            bot.guild_dict = {}
            with open(os.path.join('data', 'serverdict'), 'wb') as fd:
                pickle.dump(bot.guild_dict, fd, -1)
            logger.info('Serverdict Created')

_load_data(Dobby)

guild_dict = Dobby.guild_dict

config = {}

"""
Helper functions
"""

def load_config():
    global config
    # Load configuration
    with open('config.json', 'r') as fd:
        config = json.load(fd)

load_config()

Dobby.config = config

default_exts = ['utilities', 'locationmatching', 'eventcommands', 'badges']

for ext in default_exts:
    try:
        Dobby.load_extension(f"dobby.exts.{ext}")
    except Exception as e:
        print(f'**Error when loading extension {ext}:**\n{type(e).__name__}: {e}')
    else:
        if 'debug' in sys.argv[1:]:
            print(f'Loaded {ext} extension.')

@Dobby.command(name='load')
@checks.is_owner()
async def _load(ctx, *extensions):
    for ext in extensions:
        try:
            ctx.bot.unload_extension(f"dobby.exts.{ext}")
            ctx.bot.load_extension(f"dobby.exts.{ext}")
        except Exception as e:
            error_title = _('**Error when loading extension')
            await ctx.send(f'{error_title} {ext}:**\n'
                           f'{type(e).__name__}: {e}')
        else:
            await ctx.send(_('**Extension {ext} Loaded.**\n').format(ext=ext))

@Dobby.command(name='unload')
@checks.is_owner()
async def _unload(ctx, *extensions):
    exts = [e for e in extensions if f"exts.{e}" in Dobby.extensions]
    for ext in exts:
        ctx.bot.unload_extension(f"exts.{ext}")
    s = 's' if len(exts) > 1 else ''
    await ctx.send(_("**Extension{plural} {est} unloaded.**\n").format(plural=s, est=', '.join(exts)))

# Given a string, if it fits the pattern :emoji name:,
# and <emoji_name> is in the server's emoji list, then
# return the string <:emoji name:emoji id>. Otherwise,
# just return the string unmodified.

def parse_emoji(guild, emoji_string):
    if (emoji_string[0] == ':') and (emoji_string[-1] == ':'):
        emoji = discord.utils.get(guild.emojis, name=emoji_string.strip(':'))
        if emoji:
            emoji_string = '<:{0}:{1}>'.format(emoji.name, emoji.id)
    return emoji_string

def print_emoji_name(guild, emoji_string):
    # By default, just print the emoji_string
    ret = ('`' + emoji_string) + '`'
    emoji = parse_emoji(guild, emoji_string)
    # If the string was transformed by the parse_emoji
    # call, then it really was an emoji and we should
    # add the raw string so people know what to write.
    if emoji != emoji_string:
        ret = ((emoji + ' (`') + emoji_string) + '`)'
    return ret


def simple_gmaps_query(lat,lng):
    return f'https://www.google.com/maps/search/?api=1&query={lat},{lng}'


@Dobby.command(name='fortress', aliases=['fort'])
async def fortress(ctx, *, name):
    '''Lookup directions to a Fortress'''
    message = ctx.message
    channel = ctx.channel
    guild = ctx.guild
    fortresses = get_fortresses(guild.id)
    fortress = await location_match_prompt(channel, message.author.id, name, fortresses)
    if not fortress:
        return await channel.send(embed=discord.Embed(colour=discord.Colour.red(), description=f"No fortress found with name '{name}'. Try again using the exact fortress name!"))
    else:
        fortress_embed = discord.Embed(title=_('Click here for directions to {0}!'.format(fortress.name)), url=fortress.maps_url, colour=guild.me.colour)
        fortress_info = _("**Name:** {name}\n**Region:** {region}\n").format(name=fortress.name, region=fortress.region.title())
        fortress_embed.add_field(name=_('**Fortress Information**'), value=fortress_info, inline=False)
        return await channel.send(content="", embed=fortress_embed)

def get_fortresses(guild_id, regions=None):
    location_matching_cog = Dobby.cogs.get('LocationMatching')
    if not location_matching_cog:
        return None
    fortress = location_matching_cog.get_fortresses(guild_id, regions)
    return fortress

@Dobby.command(name='greenhouse', aliases=['gh'])
async def greenhouse(ctx, *, name):
    '''Lookup directions to a Greenhouse'''
    message = ctx.message
    channel = ctx.channel
    guild = ctx.guild
    greenhouses = get_greenhouses(guild.id)
    greenhouse = await location_match_prompt(channel, message.author.id, name, greenhouses)
    if not greenhouse:
        return await channel.send(embed=discord.Embed(colour=discord.Colour.red(), description=f"No greenhouse found with name '{name}'. Try again using the exact greenhouse name!"))
    else:
        greenhouse_embed = discord.Embed(title=_('Click here for directions to {0}!'.format(greenhouse.name)), url=greenhouse.maps_url, colour=guild.me.colour)
        greenhouse_info = _("**Name:** {name}\n**Region:** {region}\n").format(name=greenhouse.name, region=greenhouse.region.title())
        greenhouse_embed.add_field(name=_('**Fortress Information**'), value=greenhouse_info, inline=False)
        return await channel.send(content="", embed=greenhouse_embed)

def get_greenhouses(guild_id, regions=None):
    location_matching_cog = Dobby.cogs.get('LocationMatching')
    if not location_matching_cog:
        return None
    greenhouse = location_matching_cog.get_greenhouses(guild_id, regions)
    return greenhouse

async def location_match_prompt(channel, author_id, name, locations):
    # note: the following logic assumes json constraints -- no duplicates in source data
    location_matching_cog = Dobby.cogs.get('LocationMatching')
    match = None
    result = location_matching_cog.location_match(name, locations)
    results = [(match.name, score) for match, score in result]
    match = await prompt_match_result(channel, author_id, name, results)
    return next((l for l in locations if l.name == match), None)

async def prompt_match_result(channel, author_id, target, result_list):
    if not isinstance(result_list, list):
        result_list = [result_list]
    if not result_list or result_list[0] is None or result_list[0][0] is None:
        return None
    # quick check if a full match exists
    exact_match = [match for match, score in result_list if match.lower() == target.lower()]
    if len(exact_match) == 1:
        return exact_match[0]
    # reminder: partial, exact matches have 100 score, that's why this check exists
    perfect_scores = [match for match, score in result_list if score == 100]
    if len(perfect_scores) != 1:
        # one or more imperfect candidates only, ask user which to use
        sorted_result = sorted(result_list, key=lambda t: t[1], reverse=True)
        choices_list = [match for match, score in sorted_result]
        prompt = _("Didn't find an exact match for '{0}'. {1} potential matches found.").format(target, len(result_list))
        match = await utils.ask_list(Dobby, prompt, channel, choices_list, user_list=author_id)
    else:
        # found a solitary best match
        match = perfect_scores[0]
    return match

async def _print(owner, message):
    if 'launcher' in sys.argv[1:]:
        if 'debug' not in sys.argv[1:]:
            await owner.send(message)
    print(message)
    logger.info(message)

async def server_dict_save(Loop=True):
    while (not Dobby.is_closed()):
        guilddict_chtemp = copy.deepcopy(guild_dict)
        logger.info('Scheduled Server Dict Save ------ BEGIN ------')
        for guildid in guilddict_chtemp.keys():
            try:
                await _save(guildid)
                logger.info(f'Server Dict successfully save for guild with id: {guildid}')
            except Exception as err:
                logger.info('Scheduled Server Dict Save - SAVING FAILED' + str(err))
        logger.info('Scheduled Server Dict Save ------ END ------')
        await asyncio.sleep(600)
        continue

async def maint_start():
    tasks = []
    try:
        tasks.append(event_loop.create_task(server_dict_save()))
        logger.info('Maintenance Tasks Started')
    except KeyboardInterrupt:
        [task.cancel() for task in tasks]

event_loop = asyncio.get_event_loop()

"""
Events
"""
@Dobby.event
async def on_ready():
    Dobby.owner = discord.utils.get(
        Dobby.get_all_members(), id=config['master'])
    await _print(Dobby.owner, _('Starting up...'))
    Dobby.uptime = datetime.datetime.now()
    owners = []
    msg_success = 0
    msg_fail = 0
    guilds = len(Dobby.guilds)
    users = 0
    for guild in Dobby.guilds:
        users += len(guild.members)
        try:
            if guild.id not in guild_dict:
                guild_dict[guild.id] = {
                    'configure_dict':{
                        'welcome': {'enabled':False,'welcomechan':'','welcomemsg':''},
                        'invite': {'enabled':False},
                        'house':{'enabled':False, 'sort_channels': []},
                        'profession':{'enabled':False, 'sort_channels': []},
                        'settings':{'offset':0,'regional':None,'done':False,'prefix':None,'config_sessions':{}}
                    },
                    'wizards':{}
                }
            else:
                pass
        except KeyError:
            guild_dict[guild.id] = {
                'configure_dict':{
                    'welcome': {'enabled':False,'welcomechan':'','welcomemsg':''},
                    'invite': {'enabled':False},
                    'profession':{'enabled':False, 'sort_channels': []},
                    'settings':{'offset':0,'regional':None,'done':False,'prefix':None,'config_sessions':{}}
                },
                'wizards':{}
            }
        owners.append(guild.owner)
    await _print(Dobby.owner, _("{server_count} servers connected.\n{member_count} members found.").format(server_count=guilds, member_count=users))
    await maint_start()

@Dobby.event
async def on_guild_join(guild):
    owner = guild.owner
    guild_dict[guild.id] = {
        'configure_dict':{
            'welcome': {'enabled':False,'welcomechan':'','welcomemsg':''},
            'invite': {'enabled':False},
            'profession':{'enabled':False, 'sort_channels': []},
            'settings':{'offset':0,'regional':None,'done':False,'prefix':None,'config_sessions':{}}
        },
        'wizards':{}
    }
    await owner.send(_("I'm Dobby, a Discord helper bot for Wizards Unite communities, and someone has invited me to your server! Type **!help** to see a list of things I can do, and type **!configure** in any channel of your server to begin!"))

@Dobby.event
async def on_guild_remove(guild):
    try:
        if guild.id in guild_dict:
            try:
                del guild_dict[guild.id]
            except KeyError:
                pass
    except KeyError:
        pass

@Dobby.event
async def on_member_join(member):
    'Welcome message to the server and some basic instructions.'
    guild = member.guild
    house_msg = _(' or ').join(['**!sort {0}**'.format(house)
                           for house in config['house_dict'].keys()])
    if not guild_dict[guild.id]['configure_dict']['welcome']['enabled']:
        return
    # Build welcome message
    if guild_dict[guild.id]['configure_dict']['welcome'].get('welcomemsg', 'default') == "default":
        admin_message = _(' If you have any questions just ask an admin.')
        welcomemessage = _('Welcome to {server}, {user}! ')
        if guild_dict[guild.id]['configure_dict']['house']['enabled']:
            welcomemessage += _('Set your house by typing {house_command}.').format(
                house_command=house_msg)
        welcomemessage += admin_message
    else:
        welcomemessage = guild_dict[guild.id]['configure_dict']['welcome']['welcomemsg']

    if guild_dict[guild.id]['configure_dict']['welcome']['welcomechan'] == 'dm':
        send_to = member
    elif str(guild_dict[guild.id]['configure_dict']['welcome']['welcomechan']).isdigit():
        send_to = discord.utils.get(guild.text_channels, id=int(guild_dict[guild.id]['configure_dict']['welcome']['welcomechan']))
    else:
        send_to = discord.utils.get(guild.text_channels, name=guild_dict[guild.id]['configure_dict']['welcome']['welcomechan'])
    if send_to:
        if welcomemessage.startswith("[") and welcomemessage.endswith("]"):
            await send_to.send(embed=discord.Embed(colour=guild.me.colour, description=welcomemessage[1:-1].format(server=guild.name, user=member.mention)))
        else:
            await send_to.send(welcomemessage.format(server=guild.name, user=member.mention))
    else:
        return

@Dobby.event
async def on_member_update(before, after):
    # don't think this is needed right now.
    return
    guild = after.guild
    region_dict = guild_dict[guild.id]['configure_dict'].get('regions',None)
    if region_dict:
        notify_channel = region_dict.get('notify_channel',None)
        if (not before.bot) and notify_channel is not None:
            prev_roles = set([r.name for r in before.roles])
            post_roles = set([r.name for r in after.roles])
            added_roles = post_roles-prev_roles
            removed_roles = prev_roles-post_roles
            regioninfo_dict = region_dict.get('info',None)
            if regioninfo_dict:
                notify = None
                if len(added_roles) > 0:
                    # a single member update event should only ever have 1 role change
                    role = list(added_roles)[0]
                    notify = await Dobby.get_channel(notify_channel).send(f"{after.mention} you have joined the {role.capitalize()} region.")
                if len(removed_roles) > 0:
                    # a single member update event should only ever have 1 role change
                    role = list(removed_roles)[0]
                    notify = await Dobby.get_channel(notify_channel).send(f"{after.mention} you have left the {role.capitalize()} region.")
                    
                if notify:
                    await asyncio.sleep(8)
                    await notify.delete()

@Dobby.event
async def on_message(message):
    if (not message.author.bot):
        await Dobby.process_commands(message)

@Dobby.event
async def on_message_delete(message):
    guild = message.guild
    channel = message.channel
    author = message.author
    return

@Dobby.event
async def on_raw_reaction_add(payload):
    channel = Dobby.get_channel(payload.channel_id)
    try:
        message = await channel.fetch_message(payload.message_id)
    except (discord.errors.NotFound, AttributeError):
        return
    guild = message.guild
    try:
        user = guild.get_member(payload.user_id)
    except AttributeError:
        return
    return

def can_manage(user):
    if checks.is_user_dev_or_owner(config, user.id):
        return True
    for role in user.roles:
        if role.permissions.manage_messages:
            return True
    return False

"""
Admin Commands
"""
@Dobby.command(hidden=True, name="eval")
@checks.is_dev_or_owner()
async def _eval(ctx, *, body: str):
    """Evaluates a code"""
    env = {
        'bot': ctx.bot,
        'ctx': ctx,
        'channel': ctx.channel,
        'author': ctx.author,
        'guild': ctx.guild,
        'message': ctx.message
    }
    def cleanup_code(content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])
        # remove `foo`
        return content.strip('` \n')
    env.update(globals())
    body = cleanup_code(body)
    stdout = io.StringIO()
    to_compile = (f'async def func():\n{textwrap.indent(body, "  ")}')
    try:
        exec(to_compile, env)
    except Exception as e:
        return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')
    func = env['func']
    try:
        with redirect_stdout(stdout):
            ret = await func()
    except Exception as e:
        value = stdout.getvalue()
        await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
    else:
        value = stdout.getvalue()
        try:
            await ctx.message.add_reaction('\u2705')
        except:
            pass
        if ret is None:
            if value:
                paginator = commands.Paginator(prefix='```py')
                for line in textwrap.wrap(value, 80):
                    paginator.add_line(line.rstrip().replace('`', '\u200b`'))
                for p in paginator.pages:
                    await ctx.send(p)
        else:
            ctx.bot._last_result = ret
            await ctx.send(f'```py\n{value}{ret}\n```')

@Dobby.command()
@checks.is_owner()
async def save(ctx):
    """Save persistent state to file.

    Usage: !save
    File path is relative to current directory."""
    try:
        await _save(ctx.guild.id)
        logger.info('CONFIG SAVED')
    except Exception as err:
        await _print(Dobby.owner, _('Error occured while trying to save!'))
        await _print(Dobby.owner, err)

async def _save(guildid):
    with tempfile.NamedTemporaryFile('wb', dir=os.path.dirname(os.path.join('data', 'serverdict')), delete=False) as tf:
        pickle.dump(guild_dict, tf, -1)
        tempname = tf.name
    try:
        os.remove(os.path.join('data', 'serverdict_backup'))
    except OSError as e:
        pass
    try:
        os.rename(os.path.join('data', 'serverdict'), os.path.join('data', 'serverdict_backup'))
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise
    os.rename(tempname, os.path.join('data', 'serverdict'))

    location_matching_cog = Dobby.cogs.get('LocationMatching')
    if not location_matching_cog:
        await _print(Dobby.owner, 'Fortress, Inn, and Greenhouse data not saved!')
        return None


@Dobby.command()
@checks.is_owner()
async def restart(ctx):
    """Restart after saving.

    Usage: !restart.
    Calls the save function and restarts Dobby."""
    try:
        await _save(ctx.guild.id)
    except Exception as err:
        await _print(Dobby.owner, _('Error occured while trying to save!'))
        await _print(Dobby.owner, err)
    await ctx.channel.send(_('Restarting...'))
    Dobby._shutdown_mode = 26
    await Dobby.logout()

@Dobby.command()
@checks.is_owner()
async def exit(ctx):
    """Exit after saving.

    Usage: !exit.
    Calls the save function and quits the script."""
    try:
        await _save(ctx.guild.id)
    except Exception as err:
        await _print(Dobby.owner, _('Error occured while trying to save!'))
        await _print(Dobby.owner, err)
    await ctx.channel.send(_('Shutting down...'))
    Dobby._shutdown_mode = 0
    await Dobby.logout()

@Dobby.group(name='region', case_insensitive=True)
@checks.allowregion()
async def _region(ctx):
    """Handles user-region settings"""
    if ctx.invoked_subcommand == None:
        raise commands.BadArgument()

@Dobby.group(name='set', case_insensitive=True)
async def _set(ctx):
    """Changes a setting."""
    if ctx.invoked_subcommand == None:
        raise commands.BadArgument()

@_set.command()
@commands.has_permissions(manage_guild=True)
async def timezone(ctx,*, timezone: str = ''):
    """Changes server timezone."""
    try:
        timezone = float(timezone)
    except ValueError:
        await ctx.channel.send(_("I couldn't convert your answer to an appropriate timezone! Please double check what you sent me and resend a number from **-12** to **12**."))
        return
    if (not ((- 12) <= timezone <= 14)):
        await ctx.channel.send(_("I couldn't convert your answer to an appropriate timezone! Please double check what you sent me and resend a number from **-12** to **12**."))
        return
    _set_timezone(Dobby, ctx.guild, timezone)
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=guild_dict[ctx.channel.guild.id]['configure_dict']['settings']['offset'])
    await ctx.channel.send(_("Timezone has been set to: `UTC{offset}`\nThe current time is **{now}**").format(offset=timezone,now=now.strftime("%H:%M")))

def _set_timezone(bot, guild, timezone):
    bot.guild_dict[guild.id]['configure_dict']['settings']['offset'] = timezone

@_set.command()
@commands.has_permissions(manage_guild=True)
async def prefix(ctx, prefix=None):
    """Changes server prefix."""
    if prefix == 'clear':
        prefix = None
    prefix = prefix.strip()
    _set_prefix(Dobby, ctx.guild, prefix)
    if prefix != None:
        await ctx.channel.send(_('Prefix has been set to: `{}`').format(prefix))
    else:
        default_prefix = Dobby.config['default_prefix']
        await ctx.channel.send(_('Prefix has been reset to default: `{}`').format(default_prefix))

def _set_prefix(bot, guild, prefix):
    bot.guild_dict[guild.id]['configure_dict']['settings']['prefix'] = prefix

@_set.command()
async def profile(ctx):
    guild = ctx.message.guild
    author = ctx.message.author
    profile={
        "name":"",
        "level": "",
        "titles": []
             }
    name = await profile_step("What is your Wizard name?", ctx)
    if name != "SKIPPED":
        profile["name"] = name
    level = await profile_step("What is your current level?", ctx)
    if level != "SKIPPED":
        profile["level"] = level

    match = ''
    result = TitleTable.select(TitleTable.name)
    result = result.objects(Title)
    results = [o for o in result]
    titles = [r.name for r in results]
    prompt = "Choose a title (You can choose 3 total)" 
    while len(profile["titles"]) < 3:
        match = await utils.ask_list(Dobby, prompt, author, titles, user_list=[author.id])
        if match is None:
            break
        else:
            profile["titles"].append(match)

    with DobbyDB._db.atomic():
        wizard, __  = WizardTable.get_or_create(snowflake=author.id, guild=guild.id)
        wizardprofile, __  = ProfileTable.get_or_create(wizard_id=wizard)
        wizardprofile.wizardname = profile["name"]
        wizardprofile.level = profile["level"]
        wizardprofile.title_one = profile["titles"][0] if len(profile["titles"]) > 0 else ""
        wizardprofile.title_two = profile["titles"][1] if len(profile["titles"]) > 1 else ""
        wizardprofile.title_three = profile["titles"][2] if len(profile["titles"]) > 2 else ""
        wizardprofile.save()
    await author.send("Profile Updated Successfully!")

async def profile_step(text, ctx):
    guild = ctx.message.guild
    message = ctx.message
    author = message.author
    queryembed = discord.Embed(colour=discord.Colour.purple(), description=text)
    queryembed.set_footer(text="Reply with **'skip'** to skip this profile item")
    query = await author.send(embed=queryembed)
    response = await Dobby.wait_for('message', timeout=180, check=(lambda reply: reply.author == message.author))
    if response != None:
        if response.content.lower() == "skip":
            return "SKIPPED"
        else:
            return response.content
        await response.delete()

@Dobby.group(name='get', case_insensitive=True)
@commands.has_permissions(manage_guild=True)
async def _get(ctx):
    """Get a setting value"""
    if ctx.invoked_subcommand == None:
        raise commands.BadArgument()

@_get.command()
@commands.has_permissions(manage_guild=True)
async def prefix(ctx):
    """Get server prefix."""
    prefix = _get_prefix(Dobby, ctx.message)
    await ctx.channel.send(_('Prefix for this server is: `{}`').format(prefix))

@_get.command()
@commands.has_permissions(manage_guild=True)
async def perms(ctx, channel_id = None):
    """Show Dobby's permissions for the guild and channel."""
    channel = discord.utils.get(ctx.bot.get_all_channels(), id=channel_id)
    guild = channel.guild if channel else ctx.guild
    channel = channel or ctx.channel
    guild_perms = guild.me.guild_permissions
    chan_perms = channel.permissions_for(guild.me)
    req_perms = discord.Permissions(268822608)

    embed = discord.Embed(colour=ctx.guild.me.colour)
    embed.set_author(name=_('Bot Permissions'), icon_url="https://i.imgur.com/wzryVaS.png")

    wrap = functools.partial(textwrap.wrap, width=20)
    names = [wrap(channel.name), wrap(guild.name)]
    if channel.category:
        names.append(wrap(channel.category.name))
    name_len = max(len(n) for n in names)
    def same_len(txt):
        return '\n'.join(txt + ([' '] * (name_len-len(txt))))
    names = [same_len(n) for n in names]
    chan_msg = [f"**{names[0]}** \n{channel.id} \n"]
    guild_msg = [f"**{names[1]}** \n{guild.id} \n"]
    def perms_result(perms):
        data = []
        meet_req = perms >= req_perms
        result = _("**PASS**") if meet_req else _("**FAIL**")
        data.append(f"{result} - {perms.value} \n")
        true_perms = [k for k, v in dict(perms).items() if v is True]
        false_perms = [k for k, v in dict(perms).items() if v is False]
        req_perms_list = [k for k, v in dict(req_perms).items() if v is True]
        true_perms_str = '\n'.join(true_perms)
        if not meet_req:
            missing = '\n'.join([p for p in false_perms if p in req_perms_list])
            meet_req_result = _("**MISSING**")
            data.append(f"{meet_req_result} \n{missing} \n")
        if true_perms_str:
            meet_req_result = _("**ENABLED**")
            data.append(f"{meet_req_result} \n{true_perms_str} \n")
        return '\n'.join(data)
    guild_msg.append(perms_result(guild_perms))
    chan_msg.append(perms_result(chan_perms))
    embed.add_field(name=_('GUILD'), value='\n'.join(guild_msg))
    if channel.category:
        cat_perms = channel.category.permissions_for(guild.me)
        cat_msg = [f"**{names[2]}** \n{channel.category.id} \n"]
        cat_msg.append(perms_result(cat_perms))
        embed.add_field(name=_('CATEGORY'), value='\n'.join(cat_msg))
    embed.add_field(name=_('CHANNEL'), value='\n'.join(chan_msg))

    try:
        await ctx.send(embed=embed)
    except discord.errors.Forbidden:
        # didn't have permissions to send a message with an embed
        try:
            msg = _("I couldn't send an embed here, so I've sent you a DM")
            await ctx.send(msg)
        except discord.errors.Forbidden:
            # didn't have permissions to send a message at all
            pass
        await ctx.author.send(embed=embed)

@Dobby.command()
@commands.has_permissions(manage_guild=True)
async def welcome(ctx, user: discord.Member=None):
    """Test welcome on yourself or mentioned member.

    Usage: !welcome [@member]"""
    if (not user):
        user = ctx.author
    await on_member_join(user)

@Dobby.command(hidden=True,aliases=['opl'])
@commands.has_permissions(manage_guild=True)
async def outputlog(ctx):
    """Get current Dobby log.

    Usage: !outputlog
    Output is a link to hastebin."""
    with open(os.path.join('logs', 'dobby.log'), 'r', encoding='latin-1', errors='replace') as logfile:
        logdata = logfile.read()
        async with aiohttp.ClientSession() as session:
            async with session.post("https://hastebin.com/documents",data=logdata.encode('utf-8')) as post:
                post = await post.json()
                reply = "https://hastebin.com/{}".format(post['key'])
    await ctx.channel.send(reply)

@Dobby.command(aliases=['say'])
@commands.has_permissions(manage_guild=True)
async def announce(ctx, *, announce=None):
    """Repeats your message in an embed from Dobby.

    Usage: !announce [announcement]
    If the announcement isn't added at the same time as the command, Dobby will wait 3 minutes for a followup message containing the announcement."""
    message = ctx.message
    channel = message.channel
    guild = message.guild
    author = message.author
    announcetitle = 'Announcement'
    if announce == None:
        titlewait = await channel.send(_("If you would like to set a title for your announcement please reply with the title, otherwise reply with 'skip'."))
        titlemsg = await Dobby.wait_for('message', timeout=180, check=(lambda reply: reply.author == message.author))
        await titlewait.delete()
        if titlemsg != None:
            if titlemsg.content.lower() == "skip":
                pass
            else:
                announcetitle = titlemsg.content
            await titlemsg.delete()
        announcewait = await channel.send(_("I'll wait for your announcement!"))
        announcemsg = await Dobby.wait_for('message', timeout=180, check=(lambda reply: reply.author == message.author))
        await announcewait.delete()
        if announcemsg != None:
            announce = announcemsg.content
            await announcemsg.delete()
        else:
            confirmation = await channel.send(_("You took too long to send me your announcement! Retry when you're ready."))
    embeddraft = discord.Embed(colour=guild.me.colour, description=announce)
    if ctx.invoked_with == "announce":
        title = _(announcetitle)
        if Dobby.user.avatar_url:
            embeddraft.set_author(name=title, icon_url=Dobby.user.avatar_url)
        else:
            embeddraft.set_author(name=title)
    draft = await channel.send(embed=embeddraft)
    reaction_list = ['❔', '✅', '❎']
    owner_msg_add = ''
    if checks.is_owner_check(ctx):
        owner_msg_add = '🌎 '
        owner_msg_add += _('to send it to all servers, ')
        reaction_list.insert(0, '🌎')

    def check(reaction, user):
        if user.id == author.id:
            if (str(reaction.emoji) in reaction_list) and (reaction.message.id == rusure.id):
                return True
        return False
    msg = _("That's what you sent, does it look good? React with ")
    msg += "{}❔ "
    msg += _("to send to another channel, ")
    msg += "✅ "
    msg += _("to send it to this channel, or ")
    msg += "❎ "
    msg += _("to cancel")
    rusure = await channel.send(msg.format(owner_msg_add))
    try:
        timeout = False
        res, reactuser = await ask(rusure, channel, author.id, react_list=reaction_list)
    except TypeError:
        timeout = True
    if not timeout:
        await rusure.delete()
        if res.emoji == '❎':
            confirmation = await channel.send(_('Announcement Cancelled.'))
            await draft.delete()
        elif res.emoji == '✅':
            confirmation = await channel.send(_('Announcement Sent.'))
        elif res.emoji == '❔':
            channelwait = await channel.send(_('What channel would you like me to send it to?'))
            channelmsg = await Dobby.wait_for('message', timeout=60, check=(lambda reply: reply.author == message.author))
            if channelmsg.content.isdigit():
                sendchannel = Dobby.get_channel(int(channelmsg.content))
            elif channelmsg.raw_channel_mentions:
                sendchannel = Dobby.get_channel(channelmsg.raw_channel_mentions[0])
            else:
                sendchannel = discord.utils.get(guild.text_channels, name=channelmsg.content)
            if (channelmsg != None) and (sendchannel != None):
                announcement = await sendchannel.send(embed=embeddraft)
                confirmation = await channel.send(_('Announcement Sent.'))
            elif sendchannel == None:
                confirmation = await channel.send(_("That channel doesn't exist! Retry when you're ready."))
            else:
                confirmation = await channel.send(_("You took too long to send me your announcement! Retry when you're ready."))
            await channelwait.delete()
            await channelmsg.delete()
            await draft.delete()
        elif (res.emoji == '🌎') and checks.is_owner_check(ctx):
            failed = 0
            sent = 0
            count = 0
            recipients = {

            }
            embeddraft.set_footer(text='For support, contact us on our Discord server. Invite Code: hhVjAN8')
            embeddraft.colour = discord.Colour.lighter_grey()
            for guild in Dobby.guilds:
                recipients[guild.name] = guild.owner
            for (guild, destination) in recipients.items():
                try:
                    await destination.send(embed=embeddraft)
                except discord.HTTPException:
                    failed += 1
                    logger.info('Announcement Delivery Failure: {} - {}'.format(destination.name, guild))
                else:
                    sent += 1
                count += 1
            logger.info('Announcement sent to {} server owners: {} successful, {} failed.'.format(count, sent, failed))
            confirmation = await channel.send(_('Announcement sent to {} server owners: {} successful, {} failed.').format(count, sent, failed))
        await asyncio.sleep(10)
        await confirmation.delete()
    else:
        await rusure.delete()
        confirmation = await channel.send(_('Announcement Timed Out.'))
        await asyncio.sleep(10)
        await confirmation.delete()
    await asyncio.sleep(30)
    await message.delete()

@Dobby.group(case_insensitive=True, invoke_without_command=True)
@commands.has_permissions(manage_guild=True)
async def configure(ctx, *, configlist: str=""):
    """Dobby Configuration

    Usage: !configure [list]
    Dobby will DM you instructions on how to configure Dobby for your server.
    If it is not your first time configuring, you can choose a section to jump to.
    You can also include a comma separated [list] of sections from the following:
    all, house, welcome, regions, timezone"""
    await _configure(ctx, configlist)

async def _configure(ctx, configlist):
    guild = ctx.message.guild
    owner = ctx.message.author
    try:
        await ctx.message.delete()
    except (discord.errors.Forbidden, discord.errors.HTTPException):
        pass
    config_sessions = guild_dict[ctx.guild.id]['configure_dict']['settings'].setdefault('config_sessions',{}).setdefault(owner.id,0) + 1
    guild_dict[ctx.guild.id]['configure_dict']['settings']['config_sessions'][owner.id] = config_sessions
    for session in guild_dict[guild.id]['configure_dict']['settings']['config_sessions'].keys():
        if not guild.get_member(session):
            del guild_dict[guild.id]['configure_dict']['settings']['config_sessions'][session]
    config_dict_temp = getattr(ctx, 'config_dict_temp',copy.deepcopy(guild_dict[guild.id]['configure_dict']))
    firstconfig = False
    all_commands = ['sort', 'assign', 'welcome', 'regions', 'timezone', 'join']
    enabled_commands = []
    configreplylist = []
    config_error = False
    if not config_dict_temp['settings']['done']:
        firstconfig = True
    if configlist and not firstconfig:
        configlist = configlist.lower().replace("timezone","settings").split(",")
        configlist = [x.strip().lower() for x in configlist]
        diff = set(configlist) - set(all_commands)
        if diff and "all" in diff:
            configreplylist = all_commands
        elif not diff:
            configreplylist = configlist
        else:
            await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description=_("I'm sorry, I couldn't understand some of what you entered. Let's just start here.")))
    if config_dict_temp['settings']['config_sessions'][owner.id] > 1:
        await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description=_("**MULTIPLE SESSIONS!**\n\nIt looks like you have **{yoursessions}** active configure sessions. I recommend you send **cancel** first and then send your request again to avoid confusing me.\n\nYour Sessions: **{yoursessions}** | Total Sessions: **{allsessions}**").format(allsessions=sum(config_dict_temp['settings']['config_sessions'].values()),yoursessions=config_dict_temp['settings']['config_sessions'][owner.id])))
    configmessage = _("Welcome to the configuration for Dobby! I will be guiding you through some steps to get me setup on your server.\n\n**Role Setup**\nBefore you begin the configuration, please make sure my role is moved to the top end of the server role hierarchy. It can be under admins and mods, but must be above house and general roles. [Here is an example](http://i.imgur.com/c5eaX1u.png)")
    if not firstconfig and not configreplylist:
        configmessage += _("\n\n**Welcome Back**\nThis isn't your first time configuring. You can either reconfigure everything by replying with **all** or reply with a comma separated list to configure those commands. Example: `subscription, raid, wild`")
        for commandconfig in config_dict_temp.keys():
            if config_dict_temp[commandconfig].get('enabled',False):
                enabled_commands.append(commandconfig)
        configmessage += _("\n\n**Enabled Commands:**\n{enabled_commands}").format(enabled_commands=", ".join(enabled_commands))
        configmessage += _("\n\n**All Commands:**\n**all** - To redo configuration\n\
**house** - For House Assignment configuration\n**welcome** - For Welcome Message configuration\n\
**regions** - for region configuration\n**join** - For !join command configuration\n")
        configmessage += _('\n\nReply with **cancel** at any time throughout the questions to cancel the configure process.')
        await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description=configmessage).set_author(name=_('Dobby Configuration - {guild}').format(guild=guild.name), icon_url=Dobby.user.avatar_url))
        while True:
            config_error = False
            def check(m):
                return m.guild == None and m.author == owner
            configreply = await Dobby.wait_for('message', check=check)
            configreply.content = configreply.content.replace("timezone", "settings")
            if configreply.content.lower() == 'cancel':
                await owner.send(embed=discord.Embed(colour=discord.Colour.red(), description=_('**CONFIG CANCELLED!**\n\nNo changes have been made.')))
                del guild_dict[guild.id]['configure_dict']['settings']['config_sessions'][owner.id]
                return None
            elif "all" in configreply.content.lower():
                configreplylist = all_commands
                break
            else:
                configreplylist = configreply.content.lower().split(",")
                configreplylist = [x.strip() for x in configreplylist]
                for configreplyitem in configreplylist:
                    if configreplyitem not in all_commands:
                        config_error = True
                        break
            if config_error:
                await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description=_("I'm sorry I don't understand. Please reply with the choices above.")))
                continue
            else:
                break
    elif firstconfig == True:
        configmessage += _('\n\nReply with **cancel** at any time throughout the questions to cancel the configure process.')
        await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description=configmessage).set_author(name=_('Dobby Configuration - {guild}').format(guild=guild.name), icon_url=Dobby.user.avatar_url))
        configreplylist = all_commands
    try:
        if "sort" in configreplylist:
            ctx = await configuration._configure_sort(ctx, Dobby)
            if not ctx:
                return None
        if "assign" in configreplylist:
            ctx = await configuration._configure_assign(ctx, Dobby)
            if not ctx:
                return None
        if "welcome" in configreplylist:
            ctx = await configuration._configure_welcome(ctx, Dobby)
            if not ctx:
                return None
        if "regions" in configreplylist:
            ctx = await configuration._configure_regions(ctx, Dobby)
            if not ctx:
                return None
        if "settings" in configreplylist:
            ctx = await configuration._configure_settings(ctx, Dobby)
            if not ctx:
                return None
        if "join" in configreplylist:
            ctx = await configuration._configure_join(ctx, Dobby)
            if not ctx:
                return None
    finally:
        if ctx:
            ctx.config_dict_temp['settings']['done'] = True
            await ctx.channel.send("overwriting config dict")
            guild_dict[guild.id]['configure_dict'] = ctx.config_dict_temp
            await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description=_("Alright! Your settings have been saved and I'm ready to go! If you need to change any of these settings, just type **!configure** in your server again.")).set_author(name=_('Configuration Complete'), icon_url=Dobby.user.avatar_url))
        del guild_dict[guild.id]['configure_dict']['settings']['config_sessions'][owner.id]

@configure.command(name='all')
async def configure_all(ctx):
    """All settings"""
    await _configure(ctx, "all")

async def _check_sessions_and_invoke(ctx, func_ref):
    guild = ctx.message.guild
    owner = ctx.message.author
    try:
        await ctx.message.delete()
    except (discord.errors.Forbidden, discord.errors.HTTPException):
        pass
    if not guild_dict[guild.id]['configure_dict']['settings']['done']:
        await _configure(ctx, "all")
        return
    config_sessions = guild_dict[ctx.guild.id]['configure_dict']['settings'].setdefault('config_sessions',{}).setdefault(owner.id,0) + 1
    guild_dict[ctx.guild.id]['configure_dict']['settings']['config_sessions'][owner.id] = config_sessions
    if guild_dict[guild.id]['configure_dict']['settings']['config_sessions'][owner.id] > 1:
        await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description=_("**MULTIPLE SESSIONS!**\n\nIt looks like you have **{yoursessions}** active configure sessions. I recommend you send **cancel** first and then send your request again to avoid confusing me.\n\nYour Sessions: **{yoursessions}** | Total Sessions: **{allsessions}**").format(allsessions=sum(guild_dict[guild.id]['configure_dict']['settings']['config_sessions'].values()),yoursessions=guild_dict[guild.id]['configure_dict']['settings']['config_sessions'][owner.id])))
    ctx = await func_ref(ctx, Dobby)
    if ctx:
        guild_dict[guild.id]['configure_dict'] = ctx.config_dict_temp
        await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description=_("Alright! Your settings have been saved and I'm ready to go! If you need to change any of these settings, just type **!configure** in your server again.")).set_author(name=_('Configuration Complete'), icon_url=Dobby.user.avatar_url))
    del guild_dict[guild.id]['configure_dict']['settings']['config_sessions'][owner.id]

@configure.command()
async def sort(ctx):
    """!sort command settings"""
    return await _check_sessions_and_invoke(ctx, configuration._configure_sort)

@configure.command()
async def assign(ctx):
    """!assign command settings"""
    return await _check_sessions_and_invoke(ctx, configuration._configure_assign)

@configure.command()
async def welcome(ctx):
    """Welcome message settings"""
    return await _check_sessions_and_invoke(ctx, configuration._configure_welcome)

@configure.command()
async def regions(ctx):
    """region configuration for server"""
    return await _check_sessions_and_invoke(ctx, configuration._configure_regions)

@configure.command()
async def join(ctx):
    """!join settings"""
    return await _check_sessions_and_invoke(ctx, configuration._configure_join)

@configure.command(aliases=['settings'])
async def timezone(ctx):
    """Configure timezone and other settings"""
    return await _check_sessions_and_invoke(ctx, configuration._configure_settings)


@Dobby.command()
@checks.is_owner()
async def reload_json(ctx):
    """Reloads the JSON files for the server

    Usage: !reload_json"""
    load_config()
    await ctx.message.add_reaction('☑')


"""
Miscellaneous
"""

@Dobby.command(name='uptime')
async def cmd_uptime(ctx):
    "Shows Dobby's uptime"
    guild = ctx.guild
    channel = ctx.channel
    embed_colour = guild.me.colour or discord.Colour.lighter_grey()
    uptime_str = await _uptime(Dobby)
    embed = discord.Embed(colour=embed_colour, icon_url=Dobby.user.avatar_url)
    embed.add_field(name=_('Uptime'), value=uptime_str)
    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        await channel.send(_('I need the `Embed links` permission to send this'))

async def _uptime(bot):
    'Shows info about Dobby'
    time_start = bot.uptime
    time_now = datetime.datetime.now()
    ut = relativedelta(time_now, time_start)
    (ut.years, ut.months, ut.days, ut.hours, ut.minutes)
    if ut.years >= 1:
        uptime = _('{yr}y {mth}m {day}d {hr}:{min}').format(yr=ut.years, mth=ut.months, day=ut.days, hr=ut.hours, min=ut.minutes)
    elif ut.months >= 1:
        uptime = _('{mth}m {day}d {hr}:{min}').format(mth=ut.months, day=ut.days, hr=ut.hours, min=ut.minutes)
    elif ut.days >= 1:
        uptime = _('{day} days {hr} hrs {min} mins').format(day=ut.days, hr=ut.hours, min=ut.minutes)
    elif ut.hours >= 1:
        uptime = _('{hr} hrs {min} mins {sec} secs').format(hr=ut.hours, min=ut.minutes, sec=ut.seconds)
    else:
        uptime = _('{min} mins {sec} secs').format(min=ut.minutes, sec=ut.seconds)
    return uptime

@Dobby.command()
async def about(ctx):
    'Shows info about Dobby'
    repo_url = 'https://github.com/tehstone/Dobby'
    owner = Dobby.owner
    channel = ctx.channel
    uptime_str = await _uptime(Dobby)
    yourserver = ctx.message.guild.name
    yourmembers = len(ctx.message.guild.members)
    embed_colour = ctx.guild.me.colour or discord.Colour.lighter_grey()
    about = _("I'm Dobby! A Wizards Unite helper bot for Discord!\n\nFor questions or feedback regarding Dobby, please contact us on [our GitHub repo]({repo_url})\n\n").format(repo_url=repo_url)
    member_count = 0
    guild_count = 0
    for guild in Dobby.guilds:
        guild_count += 1
        member_count += len(guild.members)
    embed = discord.Embed(colour=embed_colour, icon_url=Dobby.user.avatar_url)
    embed.add_field(name=_('About Dobby'), value=about, inline=False)
    embed.add_field(name=_('Owner'), value=owner)
    if guild_count > 1:
        embed.add_field(name=_('Servers'), value=guild_count)
        embed.add_field(name=_('Members'), value=member_count)
    embed.add_field(name=_("Your Server"), value=yourserver)
    embed.add_field(name=_("Your Members"), value=yourmembers)
    embed.add_field(name=_('Uptime'), value=uptime_str)
    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        await channel.send(_('I need the `Embed links` permission to send this'))

@Dobby.command()
@checks.allowsort()
async def gryffindor(ctx):
    await _sort(ctx, 'gryffindor')

@Dobby.command()
@checks.allowsort()
async def ravenclaw(ctx):
    await _sort(ctx, 'ravenclaw')

@Dobby.command()
@checks.allowsort()
async def slytherin(ctx):
    await _sort(ctx, 'slytherin')

@Dobby.command()
@checks.allowsort()
async def hufflepuff(ctx):
    await _sort(ctx, 'hufflepuff')

@Dobby.command()
@checks.allowsort()
async def sort(ctx,*,content):
    await _sort(ctx, content)

async def _sort(ctx, content):
    """Set your house.

    Usage: !sort <house name>
    The sort roles have to be created manually beforehand by the server administrator."""

    guild = ctx.guild
    toprole = guild.me.top_role.name
    position = guild.me.top_role.position
    house_msg = _(' or ').join(['**!sort {0}**'.format(house) for house in config['house_dict'].keys()])
    high_roles = []
    guild_roles = []
    lowercase_roles = []
    for role in guild.roles:
        if (role.name.lower() in config['house_dict']) and (role.name not in guild_roles):
            guild_roles.append(role.name)
    lowercase_roles = [element.lower() for element in guild_roles]
    for house in config['house_dict'].keys():
        if house.lower() not in lowercase_roles:
            try:
                temp_role = await guild.create_role(name=house.lower(), hoist=False, mentionable=True)
                guild_roles.append(house.lower())
            except discord.errors.HTTPException:
                await message.channel.send(_('Maximum guild roles reached.'))
                return
            if temp_role.position > position:
                high_roles.append(temp_role.name)
    if high_roles:
        await ctx.channel.send(_('My roles are ranked lower than the following house roles: **{higher_roles_list}**\nPlease get an admin to move my roles above them!').format(higher_roles_list=', '.join(high_roles)))
        return
    role = None
    house_split = content.lower().split()
    entered_house = house_split[0]
    entered_house = ''.join([i for i in entered_house if i.isalpha()])
    if entered_house in lowercase_roles:
        index = lowercase_roles.index(entered_house)
        role = discord.utils.get(ctx.guild.roles, name=guild_roles[index])
    # Check if user already belongs to a house role by
    # getting the role objects of all houses in house_dict and
    # checking if the message author has any of them.
    for house in guild_roles:
        temp_role = discord.utils.get(ctx.guild.roles, name=house)
        if temp_role:
            # and the user has this role,
            if (temp_role in ctx.author.roles):
                # then report that a role is already assigned
                await ctx.channel.send(_('You already have a house role!'))
                return
        # If the role isn't valid, something is misconfigured, so fire a warning.
        else:
            await ctx.channel.send(_('{house_role} is not configured as a role on this server. Please contact an admin for assistance.').format(house_role=house))
            return
    # Check if house is one of the three defined in the house_dict
    if entered_house not in config['house_dict'].keys():
        await ctx.channel.send(_('"{entered_house}" isn\'t a valid house! Try {available_houses}').format(entered_house=entered_house, available_houses=house_msg))
        return
    # Check if the role is configured on the server
    elif role == None:
        await ctx.channel.send(_('The "{entered_house}" role isn\'t configured on this server! Contact an admin!').format(entered_house=entered_house))
    else:
        try:
            await ctx.author.add_roles(role)
            await ctx.channel.send(_('Added {member} to House {house_name}! {house_emoji}').format(member=ctx.author.mention, house_name=role.name.capitalize(), house_emoji=parse_emoji(ctx.guild, config['house_dict'][entered_house])))
        except discord.Forbidden:
            await ctx.channel.send(_("I can't add roles!"))

@Dobby.command()
@checks.allowassign()
async def auror(ctx):
    await _assign(ctx, 'auror')

@Dobby.command()
@checks.allowassign()
async def professor(ctx):
    await _assign(ctx, 'professor')

@Dobby.command()
@checks.allowassign()
async def magizoologist(ctx):
    await _assign(ctx, 'magizoologist')

@Dobby.command()
@checks.allowassign()
async def assign(ctx,*,content):
    await _assign(ctx, content)

async def _assign(ctx, content):
    """Set your profession.

    Usage: !assign <profession name>
    The sort roles have to be created manually beforehand by the server administrator."""

    guild = ctx.guild
    toprole = guild.me.top_role.name
    position = guild.me.top_role.position
    profession_msg = _(' or ').join(['**!sort {0}**'.format(house) for house in config['profession_dict'].keys()])
    high_roles = []
    guild_roles = []
    lowercase_roles = []
    for role in guild.roles:
        if (role.name.lower() in config['profession_dict']) and (role.name not in guild_roles):
            guild_roles.append(role.name)
    lowercase_roles = [element.lower() for element in guild_roles]
    for profession in config['profession_dict'].keys():
        if profession.lower() not in lowercase_roles:
            try:
                temp_role = await guild.create_role(name=profession.lower(), hoist=False, mentionable=True)
                guild_roles.append(profession.lower())
            except discord.errors.HTTPException:
                await message.channel.send(_('Maximum guild roles reached.'))
                return
            if temp_role.position > position:
                high_roles.append(temp_role.name)
    if high_roles:
        await ctx.channel.send(_('My roles are ranked lower than the following profession roles: **{higher_roles_list}**\nPlease get an admin to move my roles above them!').format(higher_roles_list=', '.join(high_roles)))
        return
    role = None
    profession_split = content.lower().split()
    entered_profession = profession_split[0]
    entered_profession = ''.join([i for i in entered_profession if i.isalpha()])
    if entered_profession in lowercase_roles:
        index = lowercase_roles.index(entered_profession)
        role = discord.utils.get(ctx.guild.roles, name=guild_roles[index])
    # Check if user already belongs to a profession role by
    # getting the role objects of all professions in profession_dict and
    # checking if the message author has any of them.
    for profession in guild_roles:
        temp_role = discord.utils.get(ctx.guild.roles, name=profession)
        if temp_role:
            # and the user has this role,
            if (temp_role in ctx.author.roles):
                # then report that a role is already assigned
                await ctx.channel.send(_('You already have a profession role!'))
                return
        # If the role isn't valid, something is misconfigured, so fire a warning.
        else:
            await ctx.channel.send(f'{profession} is not configured as a role on this server. Please contact an admin for assistance.')
            return
    # Check if profession is one of the three defined in the profession_dict
    if entered_profession not in config['profession_dict'].keys():
        await ctx.channel.send(f'"{entered_profession}" isn\'t a valid house! Try {profession_msg}')
        return
    # Check if the role is configured on the server
    elif role == None:
        await ctx.channel.send(f'The "{entered_profession}" role isn\'t configured on this server! Contact an admin!')
    else:
        try:
            await ctx.author.add_roles(role)
            await ctx.channel.send(f"Added {ctx.author.mention} to {role.name.capitalize()}! {parse_emoji(ctx.guild, config['profession_dict'][entered_profession])}")
        except discord.Forbidden:
            await ctx.channel.send("I can't add roles!")

@Dobby.command(hidden=True)
async def profile(ctx, user: discord.Member = None):
    """Displays a user's profile.

    Usage:!profile [user]"""
    if not user:
        user = ctx.message.author
    wizard, __  = WizardTable.get_or_create(snowflake=user.id, guild=ctx.guild.id)
    wizardprofile, __  = ProfileTable.get_or_create(wizard_id=wizard)
    embed = discord.Embed(title=_("{user}\'s Wizard Profile").format(user=user.display_name), colour=user.colour)
    embed.set_thumbnail(url=user.avatar_url)
    await ctx.send(embed=embed)

@Dobby.command(aliases=["invite"])
@checks.allowjoin()
async def join(ctx):
    channel = ctx.message.channel
    guild = ctx.message.guild
    join_dict = guild_dict[guild.id]['configure_dict'].setdefault('join')
    if join_dict.get('enabled', False):
        return await channel.send(join_dict['link'])

"""
Reporting
"""
async def _send_notifications_async(type, details, new_channel, exclusions=[]):
    return

async def _generate_role_notification_async(role_name, channel, outbound_dict):
    if len(outbound_dict) == 0:
        return
    guild = channel.guild
    # generate new role
    temp_role = await guild.create_role(name=role_name, hoist=False, mentionable=True)
    for trainer in outbound_dict.values():
        await trainer['discord_obj'].add_roles(temp_role)
    # send notification message in channel
    obj = next(iter(outbound_dict.values()))
    message = obj['message']
    msg_obj = await channel.send(f'~{temp_role.mention} {message}')
    async def cleanup():
        await asyncio.sleep(300)
        await temp_role.delete()
        await msg_obj.delete()
    asyncio.ensure_future(cleanup())

"""
Data Management Commands
"""
@Dobby.group(name="loc")
async def _loc(ctx):
    """Location data management command"""
    if ctx.invoked_subcommand == None:
        raise commands.BadArgument()

@_loc.command(name="add")
@commands.has_permissions(manage_guild=True)
async def _loc_add(ctx, *, info):
    """Adds a new location to the database

    Requires type (fortress/inn/greenhouse), name, region name, latitude, longitude in that order."""
    channel = ctx.channel
    message = ctx.message
    type = None
    name = None
    region = None
    latitude = None
    longitude = None
    error_msg = None
    try:
        if ',' in info:
            info_split = info.split(',')
            if len(info_split) < 5:
                error_msg = "Please provide the following when using this command: `location type, name, region, latitude, longitude`"
            elif len(info_split) == 5:
                type, name, region, latitude, longitude = [x.strip() for x in info.split(',')]
        else:
            error_msg = "Please provide the following when using this command: `location type, name, region, latitude, longitude`"
    except:
        error_msg = "Please provide the following when using this command: `location type, name, region, latitude, longitude`"
    if error_msg is not None:
        return await channel.send(error_msg)
    data = {}
    data["coordinates"] = f"{latitude},{longitude}"
    data["region"] = region.lower()
    data["guild"] = str(ctx.guild.id)
    error_msg = LocationTable.create_location(name, data, type)
    if error_msg is None:
        success = await channel.send(embed=discord.Embed(colour=discord.Colour.green(), description=f"Successfully added {type}: {name}."))
        await message.add_reaction('✅')
        await asyncio.sleep(10)
        await success.delete()
        return
    else:
        failed = await channel.send(embed=discord.Embed(colour=discord.Colour.red(), description=f"Failed to add {type}: {name}."))
        await message.add_reaction('❌')        
        await asyncio.sleep(10)
        await failed.delete()
        return

    
@_loc.command(name="changeregion", aliases=["cr"])
@commands.has_permissions(manage_guild=True)
async def _loc_change_region(ctx, *, info):
    """Changes the region associated with a Location.

    Requires type (fortress/inn/greenhouse), the name of the location,
    and the name of the new region it should be assigned to."""
    channel = ctx.channel
    message = ctx.message
    author = message.author
    info = [x.strip() for x in info.split(',')]
    inn, greenhouse, fortress = None, None
    if len(info) != 3:
        failed = await channel.send(embed=discord.Embed(colour=discord.Colour.red(), description=f"Please provide (comma separated) the location type (fortress/inn/greenhouse), name of the location, and the new region it should be assigned to."))
        await message.add_reaction('❌')        
        await asyncio.sleep(10)
        await failed.delete()
        return
    if info[0].lower() == "inn":
        inns = get_inns(ctx.guild.id, None)
        inn = await location_match_prompt(channel, author.id, info[1], inns)
        if inn is not None:
            name = inn.name
    elif info[0].lower() == "greenhouse":
        greenhouses = get_greenhouses(ctx.guild.id, None)
        greenhouse = await location_match_prompt(channel, author.id, info[1], greenhouses)
        if greenhouse is not None:
            name = greenhouse.name
    elif info[0].lower() == "fortress":
        fortresses = get_fortresses(ctx.guild.id, None)
        fortress = await location_match_prompt(channel, author.id, info[1], fortresses)
        if fortress is not None:
            name = fortress.name
    if not inn and not greenhouse and not fortress:
        failed = await channel.send(embed=discord.Embed(colour=discord.Colour.red(), description=f"No {info[0]} found with name {info[1]}."))
        await message.add_reaction('❌')        
        await asyncio.sleep(10)
        await failed.delete()
        return
    result = await changeRegion(ctx, name, info[2])
    if result == 0:
        failed = await channel.send(embed=discord.Embed(colour=discord.Colour.red(), description=f"Failed to change location for {name}."))
        await message.add_reaction('❌')        
        await asyncio.sleep(10)
        await failed.delete()
        return
    else:
        success = await channel.send(embed=discord.Embed(colour=discord.Colour.green(), description=f"Successfully changed location for {name}."))
        await message.add_reaction('✅')
        await asyncio.sleep(10)
        await success.delete()
        return

@_loc.command(name="deletelocation", aliases=["del"])
@commands.has_permissions(manage_guild=True)
async def _loc_deletelocation(ctx, *, info):
    """Removes a location from the database

    Requires type (fortress/inn/greenhouse) and the name of the location.
    Requires no confirmation, will delete as soon as the
    correct location is identified."""
    channel = ctx.channel
    message = ctx.message
    author = message.author
    info = info.split(',')
    if len(info) != 2:
        failed = await channel.send(embed=discord.Embed(colour=discord.Colour.red(), description=f"Please provide (comma separated) the location type (fortress, inn, or greenhouse) and the name of the location."))
        await message.add_reaction('❌')        
        await asyncio.sleep(10)
        await failed.delete()
        return
    type = info[0].lower()
    inn, greenhouse, fortress = None
    if type == "inn":
        inns = get_inns(ctx.guild.id, None)
        inn = await location_match_prompt(channel, author.id, info[1], inns)
        if inn is not None:
            name = inn.name
    elif type == "greenhouse":
        greenhouses = get_greenhouses(ctx.guild.id, None)
        greenhouse = await location_match_prompt(channel, author.id, info[1], greenhouses)
        if greenhouse is not None:
            name = greenhouse.name
    elif type == "fortress":
        fortresses = get_fortresses(ctx.guild.id, None)
        fortress = await location_match_prompt(channel, author.id, info[1], fortresses)
        if fortress is not None:
            name = fortress.name
    if not inn and not greenhouse and not fortress:
        failed = await channel.send(embed=discord.Embed(colour=discord.Colour.red(), description=f"No {info[0]} found with name {info[1]}."))
        await message.add_reaction('❌')        
        await asyncio.sleep(10)
        await failed.delete()
        return
    result = await deleteLocation(ctx, type, name)
    if result == 0:
        failed = await channel.send(embed=discord.Embed(colour=discord.Colour.red(), description=f"Failed to delete {type}: {name}."))
        await message.add_reaction('❌')        
        await asyncio.sleep(10)
        await failed.delete()
        return
    else:
        success = await channel.send(embed=discord.Embed(colour=discord.Colour.green(), description=f"Successfully deleted {type}: {name}."))
        await message.add_reaction('✅')
        await asyncio.sleep(10)
        await success.delete()
        return

async def deleteLocation(ctx, type, name):
    channel = ctx.channel
    guild = ctx.guild
    deleted = 0
    with DobbyDB._db.atomic() as txn:
        try:
            locationresult = (LocationTable
                .get((LocationTable.guild == guild.id) &
                       (LocationTable.name == name)))
            location = LocationTable.get_by_id(locationresult)
            loc_reg = (LocationRegionRelation
                .get(LocationRegionRelation.location_id == locationresult))
            if type == "inn":
                deleted = InnTable.delete().where(InnTable.location_id == locationresult).execute()
            elif type == "greenhouse":
                deleted = GreenhouseTable.delete().where(GreenhouseTable.location_id == locationresult).execute()
            elif type == "fortress":
                deleted = FortressTable.delete().where(FortressTable.location_id == locationresult).execute()
            deleted += LocationRegionRelation.delete().where(LocationRegionRelation.id == loc_reg).execute()
            deleted += location.delete_instance()
            txn.commit()
        except Exception as e: 
            await channel.send(e)
            txn.rollback()
    return deleted


async def changeRegion(ctx, name, region):
    region = region.lower()
    success = 0
    with DobbyDB._db.atomic() as txn:
        try:
            current = (LocationTable
                      .select(LocationTable.id.alias('loc_id'))
                      .join(LocationRegionRelation)
                      .join(RegionTable)
                      .where((LocationTable.guild == ctx.guild.id) &
                             (LocationTable.guild == RegionTable.guild) &
                             (LocationTable.name == name)))
            loc_id = current[0].loc_id
            current = (RegionTable
                       .select(RegionTable.id.alias('reg_id'))
                       .join(LocationRegionRelation)
                       .join(LocationTable)
                       .where((LocationTable.guild == ctx.guild.id) &
                              (LocationTable.guild == RegionTable.guild) &
                              (LocationTable.id == loc_id)))
            reg_id = current[0].reg_id
            deleted = LocationRegionRelation.delete().where((LocationRegionRelation.location_id == loc_id) &
                                                            (LocationRegionRelation.region_id == reg_id)).execute()
            new = (RegionTable
                   .select(RegionTable.id)
                   .where((RegionTable.name == region) &
                          (RegionTable.guild_id == ctx.guild.id)))
            success = LocationRegionRelation.create(location=loc_id, region=new[0].id)
        except Exception as e: 
            await ctx.channel.send(e)
            txn.rollback()
    return success


@Dobby.command(name="refresh_listings", hidden=True)
@commands.has_permissions(manage_guild=True)
async def _refresh_listing_channels(ctx, type, *, regions=None):
    if regions:
        regions = [r.strip() for r in regions.split(',')]
    await _update_listing_channels(ctx.guild, type, edit=True, regions=regions)
    await ctx.message.add_reaction('\u2705')

async def _refresh_listing_channels_internal(guild, type, *, regions=None):
    if regions:
        regions = [r.strip() for r in regions.split(',')]
    await _update_listing_channels(guild, type, edit=True, regions=regions)

async def _update_listing_channels(guild, type, edit=False, regions=None):
    valid_types = []
    if type not in valid_types:
        return
    listing_dict = guild_dict[guild.id]['configure_dict'].get(type, {}).get('listings', None)
    if not listing_dict or not listing_dict['enabled']:
        return
    if 'channel' in listing_dict:
        channel = Dobby.get_channel(listing_dict['channel']['id'])
        return await _update_listing_channel(channel, type, edit)
    if 'channels' in listing_dict:
        if not regions:
            regions = [r for r in listing_dict['channels']]
        for region in regions:
            channel_list = listing_dict['channels'].get(region, [])
            if not isinstance(channel_list, list):
                channel_list = [channel_list]
            for channel_info in channel_list:
                channel = Dobby.get_channel(channel_info['id'])
                await _update_listing_channel(channel, type, edit, region=region)

async def _update_listing_channel(channel, type, edit, region=None):
    lock = asyncio.Lock()
    async with lock:
        listing_dict = guild_dict[channel.guild.id]['configure_dict'].get(type, {}).get('listings', None)
        if not listing_dict or not listing_dict['enabled']:
            return
        new_messages = await _get_listing_messages(type, channel, region)
        previous_messages = await _get_previous_listing_messages(type, channel, region)
        matches = itertools.zip_longest(new_messages, previous_messages)
        new_ids = []
        for pair in matches:
            new_message = pair[0]
            old_message = pair[1]
            if pair[1]:
                try:
                    old_message = await channel.fetch_message(old_message)
                except:
                    old_message = None
            if new_message:
                new_embed = discord.Embed(description=new_message, colour=channel.guild.me.colour)
                if old_message:
                    if edit:
                        await old_message.edit(embed=new_embed)
                        new_ids.append(old_message.id)
                        continue
                    else:
                        await old_message.delete()
                new_message_obj = await channel.send(embed=new_embed)
                new_ids.append(new_message_obj.id)
            else: # old_message must be something if new_message is nothing
                await old_message.delete()
        if 'channel' in listing_dict:
            listing_dict['channel']['messages'] = new_ids
        elif 'channels' in listing_dict:
            listing_dict['channels'][region]['messages'] = new_ids
        guild_dict[channel.guild.id]['configure_dict'][type]['listings'] = listing_dict

async def _get_previous_listing_messages(type, channel, region=None):
    listing_dict = guild_dict[channel.guild.id]['configure_dict'].get(type, {}).get('listings', None)
    if not listing_dict or not listing_dict['enabled']:
        return
    previous_messages = []
    if 'channel' in listing_dict:
        previous_messages = listing_dict['channel'].get('messages', [])
    elif 'channels' in listing_dict:
        if region:
            previous_messages = listing_dict['channels'].get(region, {}).get('messages', [])
        else:
            for region, channel_info in listing_dict['channels'].items():
                if channel_info['id'] == channel.id:
                    previous_messages = channel_info.get('messages', [])
                    break
    else:
        message_history = []
        message_history = await channel.history(reverse=True).flatten()
        if len(message_history) >= 1:
            search_text = f"active {type}"
            for message in message_history:
                if search_text in message.embeds[0].description.lower():
                    previous_messages.append(message.id)
                    break
    return previous_messages

try:
    event_loop.run_until_complete(Dobby.start(config['bot_token']))
except discord.LoginFailure:
    logger.critical('Invalid token')
    event_loop.run_until_complete(Dobby.logout())
    Dobby._shutdown_mode = 0
except KeyboardInterrupt:
    logger.info('Keyboard interrupt detected. Quitting...')
    event_loop.run_until_complete(Dobby.logout())
    Dobby._shutdown_mode = 0
except Exception as e:
    logger.critical('Fatal exception', exc_info=e)
    event_loop.run_until_complete(Dobby.logout())
finally:
    pass
try:
    sys.exit(Dobby._shutdown_mode)
except AttributeError:
    sys.exit(0)
