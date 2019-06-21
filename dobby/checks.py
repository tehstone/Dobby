
from discord.ext import commands
import discord.utils
from dobby import errors

def is_user_owner_check(config,userid):
    owner = config['master']
    return userid == owner

def is_user_dev_check(userid):
    dev_list = [454869333764603904,371387628093833216]
    return userid in dev_list

def is_user_dev_or_owner(config,userid):
    if is_user_dev_check(userid) or is_user_owner_check(config,userid):
        return True
    else:
        return False

def is_owner_check(ctx):
    author = ctx.author.id
    owner = ctx.bot.config['master']
    return author == owner

def is_owner():
    return commands.check(is_owner_check)

def is_dev_check(ctx):
    author = ctx.author.id
    dev_list = [454869333764603904,371387628093833216]
    return author in dev_list

def is_dev_or_owner():
    def predicate(ctx):
        if is_dev_check(ctx) or is_owner_check(ctx):
            return True
        else:
            return False
    return commands.check(predicate)

def check_permissions(ctx, perms):
    if not perms:
        return False
    ch = ctx.channel
    author = ctx.author
    resolved = ch.permissions_for(author)
    return all((getattr(resolved, name, None) == value for (name, value) in perms.items()))

def role_or_permissions(ctx, check, **perms):
    if check_permissions(ctx, perms):
        return True
    ch = ctx.channel
    author = ctx.author
    if ch.is_private:
        return False
    role = discord.utils.find(check, author.roles)
    return role is not None

def serverowner_or_permissions(**perms):
    def predicate(ctx):
        owner = ctx.guild.owner
        if ctx.author.id == owner.id:
            return True
        return check_permissions(ctx, perms)
    return commands.check(predicate)

def serverowner():
    return serverowner_or_permissions()

#configuration
def check_welcomeset(ctx):
    if ctx.guild is None:
        return False
    guild = ctx.guild
    return ctx.bot.guild_dict[guild.id]['configure_dict']['welcome'].get('enabled',False)

def check_adminchannel(ctx):
    if ctx.guild is None:
        return False
    channel = ctx.channel
    guild = ctx.guild
    channel_list = [x for x in ctx.bot.guild_dict[guild.id]['configure_dict'].get('admin',{}).get('command_channels',[])]
    return channel.id in channel_list

def check_sortset(ctx):
    if ctx.guild is None:
        return False
    guild = ctx.guild
    return ctx.bot.guild_dict[guild.id]['configure_dict'].get('house', {}).get('enabled',False)

def check_sortchannel(ctx):
    if ctx.guild is None:
        return False
    channel = ctx.channel
    guild = ctx.guild
    sort_channels = ctx.bot.guild_dict[guild.id]['configure_dict'].get('house', {}).get('sort_channels',[])
    return channel.id in sort_channels

def check_assignset(ctx):
    if ctx.guild is None:
        return False
    guild = ctx.guild
    return ctx.bot.guild_dict[guild.id]['configure_dict'].get('profession', {}).get('enabled',False)

def check_assignchannel(ctx):
    if ctx.guild is None:
        return False
    channel = ctx.channel
    guild = ctx.guild
    assign_channels = ctx.bot.guild_dict[guild.id]['configure_dict'].get('profession', {}).get('sort_channels',[])
    return channel.id in assign_channels

#Decorators
def allowregion():
    def predicate(ctx):
        return True
    return commands.check(predicate)

def allowsort():
    def predicate(ctx):
        if check_sortset(ctx):
            if check_sortchannel(ctx):
                return True
            else:
                raise errors.SortChannelCheckFail()
        raise errors.SortSetCheckFail()
    return commands.check(predicate)

def allowassign():
    def predicate(ctx):
        if check_assignset(ctx):
            if check_assignchannel(ctx):
                return True
            else:
                raise errors.AssignChannelCheckFail()
        raise errors.AssignSetCheckFail()
    return commands.check(predicate)

def allowjoin():
    def predicate(ctx):
        return True
    return commands.check(predicate)

def feature_enabled(names, ensure_all=False):
    def predicate(ctx):
        cfg = ctx.bot.guild_dict[ctx.guild.id]['configure_dict']
        enabled = [k for k, v in cfg.items() if v.get('enabled', False)]
        if isinstance(names, list):
            result = [n in enabled for n in names]
            return all(*result) if ensure_all else any(*result)
        if isinstance(names, str):
            return names in enabled
    return commands.check(predicate)
