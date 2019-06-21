import re

from fuzzywuzzy import fuzz
from fuzzywuzzy import process

import discord
import asyncio

def get_match(word_list: list, word: str, score_cutoff: int = 60, isPartial: bool = False, limit: int = 1):
    """Uses fuzzywuzzy to see if word is close to entries in word_list

    Returns a tuple of (MATCH, SCORE)
    """
    result = None
    scorer = fuzz.ratio
    if isPartial:
        scorer = fuzz.partial_ratio
    if limit == 1:
        result = process.extractOne(word, word_list, 
            scorer=scorer, score_cutoff=score_cutoff)  
    else:
        result = process.extractBests(word, word_list, 
            scorer=scorer, score_cutoff=score_cutoff, limit=limit)
    if not result:
        return (None, None)
    return result

def colour(*args):
    """Returns a discord Colour object.

    Pass one as an argument to define colour:
        `int` match colour value.
        `str` match common colour names.
        `discord.Guild` bot's guild colour.
        `None` light grey.
    """
    arg = args[0] if args else None
    if isinstance(arg, int):
        return discord.Colour(arg)
    if isinstance(arg, str):
        colour = arg
        try:
            return getattr(discord.Colour, colour)()
        except AttributeError:
            return discord.Colour.lighter_grey()
    if isinstance(arg, discord.Guild):
        return arg.me.colour
    else:
        return discord.Colour.lighter_grey()

def make_embed(msg_type='', title=None, icon=None, content=None,
               msg_colour=None, guild=None, title_url=None,
               thumbnail='', image='', fields=None, footer=None,
               footer_icon=None, inline=False):
    """Returns a formatted discord embed object.

    Define either a type or a colour.
    Types are:
    error, warning, info, success, help.
    """

    embed_types = {
        'error':{
            'icon':'https://i.imgur.com/juhq2uJ.png',
            'colour':'red'
        },
        'warning':{
            'icon':'https://i.imgur.com/4JuaNt9.png',
            'colour':'gold'
        },
        'info':{
            'icon':'https://i.imgur.com/wzryVaS.png',
            'colour':'blue'
        },
        'success':{
            'icon':'https://i.imgur.com/ZTKc3mr.png',
            'colour':'green'
        },
        'help':{
            'icon':'https://i.imgur.com/kTTIZzR.png',
            'colour':'blue'
        }
    }
    if msg_type in embed_types.keys():
        msg_colour = embed_types[msg_type]['colour']
        icon = embed_types[msg_type]['icon']
    if guild and not msg_colour:
        msg_colour = colour(guild)
    else:
        if not isinstance(msg_colour, discord.Colour):
            msg_colour = colour(msg_colour)
    embed = discord.Embed(description=content, colour=msg_colour)
    if not title_url:
        title_url = discord.Embed.Empty
    if not icon:
        icon = discord.Embed.Empty
    if title:
        embed.set_author(name=title, icon_url=icon, url=title_url)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if image:
        embed.set_image(url=image)
    if fields:
        for key, value in fields.items():
            ilf = inline
            if not isinstance(value, str):
                ilf = value[0]
                value = value[1]
            embed.add_field(name=key, value=value, inline=ilf)
    if footer:
        footer = {'text':footer}
        if footer_icon:
            footer['icon_url'] = footer_icon
        embed.set_footer(**footer)
    return embed

def bold(msg: str):
    """Format to bold markdown text"""
    return f'**{msg}**'

def italics(msg: str):
    """Format to italics markdown text"""
    return f'*{msg}*'

def bolditalics(msg: str):
    """Format to bold italics markdown text"""
    return f'***{msg}***'

def code(msg: str):
    """Format to markdown code block"""
    return f'```{msg}```'

def pycode(msg: str):
    """Format to code block with python code highlighting"""
    return f'```py\n{msg}```'

def ilcode(msg: str):
    """Format to inline markdown code"""
    return f'`{msg}`'

def convert_to_bool(argument):
    lowered = argument.lower()
    if lowered in ('yes', 'y', 'true', 't', '1', 'enable', 'on'):
        return True
    elif lowered in ('no', 'n', 'false', 'f', '0', 'disable', 'off'):
        return False
    else:
        return None

def sanitize_channel_name(name):
    """Converts a given string into a compatible discord channel name."""
    # Remove all characters other than alphanumerics,
    # dashes, underscores, and spaces
    ret = re.sub('[^a-zA-Z0-9 _\\-]', '', name)
    # Replace spaces with dashes
    ret = ret.replace(' ', '-')
    return ret

async def ask(bot, message, user_list=None, timeout=60, *, react_list=['✅', '❎']):
    if user_list and not isinstance(user_list, list):
        user_list = [user_list]
    def check(reaction, user):
        if user_list and isinstance(user_list, list):
            return (user.id in user_list) and (reaction.message.id == message.id) and (reaction.emoji in react_list)
        elif not user_list:
            return (user.id != message.author.id) and (reaction.message.id == message.id) and (reaction.emoji in react_list)
    for r in react_list:
        await asyncio.sleep(0.25)
        await message.add_reaction(r)
    try:
        reaction, user = await bot.wait_for('reaction_add', check=check, timeout=timeout)
        return reaction, user
    except asyncio.TimeoutError:
        try:
            await message.clear_reactions()
        except:
            pass
        return

async def ask_list(bot, prompt, destination, choices_list, options_emoji_list=None, user_list=None, *, allow_edit=False):    
    if not choices_list:
        return None
    if not options_emoji_list:
        options_emoji_list = [str(i)+'\u20e3' for i in range(10)]
    if not isinstance(user_list, list):
        user_list = [user_list]
    next_emoji = '➡'
    next_emoji_text = '➡️'
    edit_emoji = '✏'
    edit_emoji_text = '✏️'
    cancel_emoji = '❌'
    num_pages = (len(choices_list) - 1) // len(options_emoji_list)    
    for offset in range(num_pages + 1):
        list_embed = discord.Embed(colour=destination.guild.me.colour)
        other_options = []
        emojified_options = []
        current_start = offset * len(options_emoji_list)
        current_options_emoji = options_emoji_list
        current_choices = choices_list[current_start:current_start+len(options_emoji_list)]
        try:
            if len(current_choices) < len(current_options_emoji):
                current_options_emoji = current_options_emoji[:len(current_choices)]
            for i, name in enumerate(current_choices):
                emojified_options.append(f"{current_options_emoji[i]}: {name}")
            list_embed.add_field(name=prompt, value='\n'.join(emojified_options), inline=False)
            embed_footer="Choose the reaction corresponding to the desired entry above."
            if offset != num_pages:
                other_options.append(next_emoji)
                embed_footer += f" Select {next_emoji_text} to see more options."
            if allow_edit:
                other_options.append(edit_emoji)
                embed_footer += f" To enter a custom answer, select {edit_emoji_text}."
            embed_footer += f" Select {cancel_emoji} to cancel."
            list_embed.set_footer(text=embed_footer)
            other_options.append(cancel_emoji)
            q_msg = await destination.send(embed=list_embed)
            all_options = current_options_emoji + other_options
            reaction, __ = await ask(bot, q_msg, user_list, react_list=all_options)
        except TypeError:
            return None
        if not reaction:
            return None
        await q_msg.delete()
        if reaction.emoji in current_options_emoji:
            return choices_list[current_start+current_options_emoji.index(reaction.emoji)]
        if reaction.emoji == edit_emoji:
            break
        if reaction.emoji == cancel_emoji:
            return None    
    def check(message):
        if user_list:
            return (message.author.id in user_list)
        else:
            return (message.author.id != message.guild.me.id)
    try:
        await destination.send("What's the custom value?")
        message = await bot.wait_for('message', check=check, timeout=60)
        return message.content
    except Exception:
        return None

async def check_channel_list(ctx, Dobby, channels):
    guild = ctx.guild
    channel_list = channels.content.lower().split(',')
    channel_list = [x.strip() for x in channel_list]
    guild_channel_list = []
    for channel in guild.text_channels:
        guild_channel_list.append(channel.id)
    channel_objs = []
    channel_names = []
    channel_errors = []
    for item in channel_list:
        channel = None
        if item.isdigit():
            channel = discord.utils.get(guild.text_channels, id=int(item))
        if not channel:
            item = re.sub('[^a-zA-Z0-9 _\\-]+', '', item)
            item = item.replace(" ","-")
            name = await letter_case(guild.text_channels, item.lower())
            channel = discord.utils.get(guild.text_channels, name=name)
        if channel:
            channel_objs.append(channel)
            channel_names.append(channel.name)
        else:
            channel_errors.append(item)
    channel_list = [x.id for x in channel_objs]
    diff = set(channel_list) - set(guild_channel_list)
    if (not diff) and (not channel_errors):
        result = {'status':'success', 'missed': [], 'channels': channel_list}
        for channel in channel_objs:
            ow = channel.overwrites_for(Dobby.user)
            ow.send_messages = True
            ow.read_messages = True
            ow.manage_roles = True
            try:
                await channel.set_permissions(Dobby.user, overwrite = ow)
            except (discord.errors.Forbidden, discord.errors.HTTPException, discord.errors.InvalidArgument):
                result['status'] = 'overwrites'
                result['missed'].append(channel.id)
        return result
    else:
        result['status'] = 'failed'
        result['missed'] = channel_errors
        return result

def do_template(message, author, guild):
    not_found = []

    def template_replace(match):
        if match.group(3):
            if match.group(3) == 'user':
                return '{user}'
            elif match.group(3) == 'server':
                return guild.name
            else:
                return match.group(0)
        if match.group(4):
            emoji = (':' + match.group(4)) + ':'
            return parse_emoji(guild, emoji)
        match_type = match.group(1)
        full_match = match.group(0)
        match = match.group(2)
        if match_type == '<':
            mention_match = re.search('(#|@!?|&)([0-9]+)', match)
            match_type = mention_match.group(1)[0]
            match = mention_match.group(2)
        if match_type == '@':
            member = guild.get_member_named(match)
            if match.isdigit() and (not member):
                member = guild.get_member(match)
            if (not member):
                not_found.append(full_match)
            return member.mention if member else full_match
        elif match_type == '#':
            channel = discord.utils.get(guild.text_channels, name=match)
            if match.isdigit() and (not channel):
                channel = guild.get_channel(int(match))
            if (not channel):
                not_found.append(full_match)
            return channel.mention if channel else full_match
        elif match_type == '&':
            role = discord.utils.get(guild.roles, name=match)
            if match.isdigit() and (not role):
                role = discord.utils.get(guild.roles, id=int(match))
            if (not role):
                not_found.append(full_match)
            return role.mention if role else full_match
    template_pattern = '(?i){(@|#|&|<)([^{}]+)}|{(user|server)}|<*:([a-zA-Z0-9]+):[0-9]*>*'
    msg = re.sub(template_pattern, template_replace, message)
    return (msg, not_found)