
import discord
from discord.ext import commands
from discord.ext.commands.errors import CommandError
from inspect import signature, getfullargspec
import asyncio

class SortSetCheckFail(CommandError):
    'Exception raised checks.sortset fails'
    pass

class AssignSetCheckFail(CommandError):
    'Exception raised checks.assignset fails'
    pass

class JoinSetCheckFail(CommandError):
    'Exception raised checks.joinset fails'
    pass

class RegionsSetCheckFail(CommandError):
    'Exception raised checks.regionsset fails'
    pass

class RegionChangeCheckFail(CommandError):
    'Exception raised checks.regionchange fails'
    pass

class SortChannelCheckFail(CommandError):
    'Exception raised checks.sortchannel fails'
    pass

class AssignChannelCheckFail(CommandError):
    'Exception raised checks.assignchannel fails'
    pass

async def delete_error(message, error):
    try:
        await message.delete()
    except (discord.errors.Forbidden, discord.errors.HTTPException):
        pass
    try:
        await error.delete()
    except (discord.errors.Forbidden, discord.errors.HTTPException):
        pass

def missing_arg_msg(ctx):
    prefix = ctx.prefix.replace(ctx.bot.user.mention, '@' + ctx.bot.user.name)
    command = ctx.invoked_with
    callback = ctx.command.callback
    sig = list(signature(callback).parameters.keys())
    (args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations) = getfullargspec(callback)
    rq_args = []
    nr_args = []
    if defaults:
        rqargs = args[:(- len(defaults))]
    else:
        rqargs = args
    if varargs:
        if varargs != 'args':
            rqargs.append(varargs)
    arg_num = len(ctx.args) - 1
    sig.remove('ctx')
    args_missing = sig[arg_num:]
    msg = "I'm missing some details! Usage: {prefix}{command}".format(prefix=prefix, command=command)
    for a in sig:
        if kwonlydefaults:
            if a in kwonlydefaults.keys():
                msg += ' [{0}]'.format(a)
                continue
        if a in args_missing:
            msg += ' **<{0}>**'.format(a)
        else:
            msg += ' <{0}>'.format(a)
    return msg

def custom_error_handling(bot, logger):

    @bot.event
    async def on_command_error(ctx, error):
        channel = ctx.channel
        guild = ctx.guild
        prefix = ctx.prefix.replace(ctx.bot.user.mention, '@' + ctx.bot.user.name)
        if isinstance(error, commands.MissingRequiredArgument):
            error = await ctx.channel.send(embed=discord.Embed(colour=discord.Colour.red(), description=missing_arg_msg(ctx)))
            await asyncio.sleep(10)
            await delete_error(ctx.message, error)
        elif isinstance(error, commands.BadArgument):
            formatter = commands.formatter.HelpFormatter()
            page = await formatter.format_help_for(ctx, ctx.command)
            error = await ctx.channel.send(page[0])
            await asyncio.sleep(20)
            await delete_error(ctx.message, error)
        elif isinstance(error, commands.CommandNotFound):
            pass
        elif isinstance(error, commands.CheckFailure):
            pass
        elif isinstance(error, RegionsSetCheckFail):
            msg = 'Regions are not enabled on this server. **{prefix}{cmd_name}** is unable to be used.'.format(cmd_name=ctx.invoked_with, prefix=prefix)
            error = await ctx.channel.send(msg)
            await asyncio.sleep(10)
            await delete_error(ctx.message, error)
        elif isinstance(error, JoinSetCheckFail):
            msg = 'Invite links are not enabled on this server. **{prefix}{cmd_name}** is unable to be used.'.format(cmd_name=ctx.invoked_with, prefix=prefix)
            error = await ctx.channel.send(msg)
            await asyncio.sleep(10)
            await delete_error(ctx.message, error)
        elif isinstance(error, SortSetCheckFail):
            msg = 'Sorting is not enabled on this server. **{prefix}{cmd_name}** is unable to be used.'.format(cmd_name=ctx.invoked_with, prefix=prefix)
            error = await ctx.channel.send(msg)
            await asyncio.sleep(10)
            await delete_error(ctx.message, error)
        elif isinstance(error, AssignSetCheckFail):
            msg = 'Profession assignment is not enabled on this server. **{prefix}{cmd_name}** is unable to be used.'.format(cmd_name=ctx.invoked_with, prefix=prefix)
            error = await ctx.channel.send(msg)
            await asyncio.sleep(10)
            await delete_error(ctx.message, error)
        elif isinstance(error, SortChannelCheckFail):
            msg = 'Please use **{prefix}{cmd_name}** in one of the following channels:'.format(cmd_name=ctx.invoked_with, prefix=prefix)
            sort_channels = bot.guild_dict[guild.id]['configure_dict']['house']['sort_channels']
            for c in sort_channels:
                channel = discord.utils.get(guild.channels, id=c)
                if channel:
                    msg += '\n' + channel.mention
                else:
                    msg += '\n#deleted-channel'
            error = await ctx.channel.send(embed=discord.Embed(colour=discord.Colour.red(), description=msg))
            await asyncio.sleep(10)
            await delete_error(ctx.message, error)
        elif isinstance(error, AssignChannelCheckFail):
            msg = 'Please use **{prefix}{cmd_name}** in one of the following channels:'.format(cmd_name=ctx.invoked_with, prefix=prefix)
            sort_channels = bot.guild_dict[guild.id]['configure_dict']['profession']['sort_channels']
            for c in sort_channels:
                channel = discord.utils.get(guild.channels, id=c)
                if channel:
                    msg += '\n' + channel.mention
                else:
                    msg += '\n#deleted-channel'
            error = await ctx.channel.send(embed=discord.Embed(colour=discord.Colour.red(), description=msg))
            await asyncio.sleep(10)
            await delete_error(ctx.message, error)
        elif isinstance(error, RegionChangeCheckFail):
            msg = 'Please use **{prefix}{cmd_name}** in '.format(cmd_name=ctx.invoked_with, prefix=prefix)
            city_channels = bot.guild_dict[guild.id]['configure_dict']['regions']['command_channels']
            msg += 'one of the following channels:'
            for c in city_channels:
                channel = discord.utils.get(guild.channels, id=c)
                if channel:
                    msg += '\n' + channel.mention
                else:
                    msg += '\n#deleted-channel'
            error = await ctx.channel.send(embed=discord.Embed(colour=discord.Colour.red(), description=msg))
            await asyncio.sleep(10)
            await delete_error(ctx.message, error)
        else:
            logger.exception(type(error).__name__, exc_info=error)
