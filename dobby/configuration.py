import copy
import re

import discord
from dobby import checks, utils, constants


async def _configure_sort(ctx, Dobby):
    guild_dict = Dobby.guild_dict
    config = Dobby.config
    guild = ctx.message.guild
    owner = ctx.message.author
    config_dict_temp = getattr(ctx, 'config_dict_temp',copy.deepcopy(guild_dict[guild.id]['configure_dict']))
    await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description="Sorting allows users to join their preferred House using the **!sort** command. If you have a bot that handles this already, you may want to disable this feature.\n\nIf you are to use this feature, ensure existing houses are as follows: hufflepuff, slyitherin, ravenclaw, gryffindor. These must be all lowercase letters. If they don't exist yet, I'll make some for you instead.\n\nRespond here with: **N** to disable, **Y** to enable:").set_author(name='Sorting', icon_url=Dobby.user.avatar_url))
    while True:
        housereply = await Dobby.wait_for('message', check=(lambda message: (message.guild == None) and message.author == owner))
        if housereply.content.lower() == 'y':
            config_dict_temp['house']['enabled'] = True
            guild_roles = []
            for role in guild.roles:
                if role.name.lower() in config['house_dict'] and role.name not in guild_roles:
                    guild_roles.append(role.name)
            lowercase_roles = [element.lower() for element in guild_roles]
            for house in config['house_dict'].keys():
                temp_role = discord.utils.get(guild.roles, name=house)
                if temp_role == None:
                    try:
                        await guild.create_role(name=house, hoist=False, mentionable=True)
                    except discord.errors.HTTPException:
                        pass
            await owner.send(embed=discord.Embed(colour=discord.Colour.green(), description='House Assignments enabled!'))
            await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description="If you would like to limit use of this command to certain channels, please respond with a list of channel names or ids separated by commas. Or respond here with: **N** to this command to be used from any channel.").set_author(name='Sorting', icon_url=Dobby.user.avatar_url))
            while True:
                allowedreply = await Dobby.wait_for('message', check=(lambda message: (message.guild == None) and message.author == owner))
                if allowedreply.content.lower() == 'n':
                    break
                else:
                    result = await utils.check_channel_list(ctx, Dobby, allowedreply)
                    if result['status'] == 'success':
                        await owner.send(embed=discord.Embed(colour=discord.Colour.green(), description='Sort Channels set'))
                        config_dict_temp['house']['sort_channels'] = result['channels']
                        break
                    elif result['status'] == 'overwrites':
                        await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description=f"I couldn't set my own permissions. Please ensure I have the correct permissions in {', '.join(result['missed'])} using **{ctx.prefix}get perms**."))
                        break
                    elif result['status'] == 'failed':
                        await owner.send(
                            embed=discord.Embed(
                                colour=discord.Colour.orange(), 
                                description=f"The channel list you provided doesn't match with your servers channels.\n\nThe following aren't in your server: **{', '.join(result['missed'])}**\n\nPlease double check your channel list and resend your reponse."))
            break
        elif housereply.content.lower() == 'n':
            config_dict_temp['house']['enabled'] = False
            await owner.send(embed=discord.Embed(colour=discord.Colour.red(), description='House Assignments disabled!'))
            break
        elif housereply.content.lower() == 'cancel':
            await owner.send(embed=discord.Embed(colour=discord.Colour.red(), description='**CONFIG CANCELLED!**\n\nNo changes have been made.'))
            return None
        else:
            await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description="I'm sorry I don't understand. Please reply with either **N** to disable, or **Y** to enable."))
            continue
    ctx.config_dict_temp = config_dict_temp
    return ctx

async def _configure_assign(ctx, Dobby):
    guild_dict = Dobby.guild_dict
    config = Dobby.config
    guild = ctx.message.guild
    owner = ctx.message.author
    config_dict_temp = getattr(ctx, 'config_dict_temp',copy.deepcopy(guild_dict[guild.id]['configure_dict']))
    await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description="Sorting allows users to set their Profession using the **!assign** command. If you have a bot that handles this already, you may want to disable this feature.\n\nIf you are to use this feature, ensure existing prefessions are as follows: auror, professor, magizoologist. These must be all lowercase letters. If they don't exist yet, I'll make some for you instead.\n\nRespond here with: **N** to disable, **Y** to enable:").set_author(name='Assignment', icon_url=Dobby.user.avatar_url))
    while True:
        professionreply = await Dobby.wait_for('message', check=(lambda message: (message.guild == None) and message.author == owner))
        if professionreply.content.lower() == 'y':
            config_dict_temp['profession']['enabled'] = True
            guild_roles = []
            for role in guild.roles:
                if role.name.lower() in config['profession_dict'] and role.name not in guild_roles:
                    guild_roles.append(role.name)
            lowercase_roles = [element.lower() for element in guild_roles]
            for profession in config['profession_dict'].keys():
                temp_role = discord.utils.get(guild.roles, name=profession)
                if temp_role == None:
                    try:
                        await guild.create_role(name=profession, hoist=False, mentionable=True)
                    except discord.errors.HTTPException:
                        pass
            await owner.send(embed=discord.Embed(colour=discord.Colour.green(), description='Profession Assignments enabled!'))
            await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description="If you would like to limit use of this command to certain channels, please respond with a list of channel names or ids separated by commas. Or respond here with: **N** to this command to be used from any channel.").set_author(name='Assignment', icon_url=Dobby.user.avatar_url))
            while True:
                allowedreply = await Dobby.wait_for('message', check=(lambda message: (message.guild == None) and message.author == owner))
                if allowedreply.content.lower() == 'n':
                    break
                else:
                    result = await utils.check_channel_list(ctx, Dobby, allowedreply)
                    if result['status'] == 'success':
                        await owner.send(embed=discord.Embed(colour=discord.Colour.green(), description='Assignment Channels set'))
                        config_dict_temp['profession']['sort_channels'] = result['channels']
                        break
                    elif result['status'] == 'overwrites':
                        await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description=f"I couldn't set my own permissions. Please ensure I have the correct permissions in {', '.join(result['missed'])} using **{ctx.prefix}get perms**."))
                        break
                    elif result['status'] == 'failed':
                        await owner.send(
                            embed=discord.Embed(
                                colour=discord.Colour.orange(), 
                                description=f"The channel list you provided doesn't match with your servers channels.\n\nThe following aren't in your server: **{', '.join(result['missed'])}**\n\nPlease double check your channel list and resend your reponse."))
            break
        elif professionreply.content.lower() == 'n':
            config_dict_temp['profession']['enabled'] = False
            await owner.send(embed=discord.Embed(colour=discord.Colour.red(), description='Profession Assignments disabled!'))
            break
        elif professionreply.content.lower() == 'cancel':
            await owner.send(embed=discord.Embed(colour=discord.Colour.red(), description='**CONFIG CANCELLED!**\n\nNo changes have been made.'))
            return None
        else:
            await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description="I'm sorry I don't understand. Please reply with either **N** to disable, or **Y** to enable."))
            continue
    ctx.config_dict_temp = config_dict_temp
    return ctx

async def _configure_welcome(ctx, Dobby):
    guild_dict = Dobby.guild_dict
    guild = ctx.message.guild
    owner = ctx.message.author
    config_dict_temp = getattr(ctx, 'config_dict_temp',copy.deepcopy(guild_dict[guild.id]['configure_dict']))
    welcomeconfig = 'I can welcome new members to the server with a short message. Here is an example, but it is customizable:\n\n'
    if config_dict_temp['house']['enabled']:
        welcomeconfig += f"Welcome to {guild.name}, {owner.mention}! Set your team by typing '**!team mystic**' or '**!team valor**' or '**!team instinct**' without quotations. If you have any questions just ask an admin."
    else:
        welcomeconfig += f'Welcome to {guild}, {ownere.mention}! If you have any questions just ask an admin.'
    welcomeconfig += '\n\nThis welcome message can be in a specific channel or a direct message. If you have a bot that handles this already, you may want to disable this feature.\n\nRespond with: **N** to disable, **Y** to enable:'
    await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description=welcomeconfig).set_author(name='Welcome Message', icon_url=Dobby.user.avatar_url))
    while True:
        welcomereply = await Dobby.wait_for('message', check=(lambda message: (message.guild == None) and message.author == owner))
        if welcomereply.content.lower() == 'y':
            config_dict_temp['welcome']['enabled'] = True
            await owner.send(embed=discord.Embed(colour=discord.Colour.green(), description='Welcome Message enabled!'))
            await owner.send(embed=discord.Embed(
                colour=discord.Colour.lighter_grey(),
                description=("Would you like a custom welcome message? "
                             "You can reply with **N** to use the default message above or enter your own below.\n\n"
                             "I can read all [discord formatting](https://support.discordapp.com/hc/en-us/articles/210298617-Markdown-Text-101-Chat-Formatting-Bold-Italic-Underline-) "
                             "and I have the following template tags:\n\n"
                             "**{@member}** - Replace member with user name or ID\n"
                             "**{#channel}** - Replace channel with channel name or ID\n"
                             "**{&role}** - Replace role name or ID (shows as @deleted-role DM preview)\n"
                             "**{user}** - Will mention the new user\n"
                             "**{server}** - Will print your server's name\n"
                             "Surround your message with [] to send it as an embed. **Warning:** Mentions within embeds may be broken on mobile, this is a Discord bug.")).set_author(name="Welcome Message", icon_url=Dobby.user.avatar_url))
            if config_dict_temp['welcome']['welcomemsg'] != 'default':
                await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description=config_dict_temp['welcome']['welcomemsg']).set_author(name="Current Welcome Message", icon_url=Dobby.user.avatar_url))
            while True:
                welcomemsgreply = await Dobby.wait_for('message', check=(lambda message: (message.guild == None) and (message.author == owner)))
                if welcomemsgreply.content.lower() == 'n':
                    config_dict_temp['welcome']['welcomemsg'] = 'default'
                    await owner.send(embed=discord.Embed(colour=discord.Colour.green(), description="Default welcome message set"))
                    break
                elif welcomemsgreply.content.lower() == "cancel":
                    await owner.send(embed=discord.Embed(colour=discord.Colour.red(), description="**CONFIG CANCELLED!**\n\nNo changes have been made."))
                    return None
                elif len(welcomemsgreply.content) > 500:
                    await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description=f"Please shorten your message to less than 500 characters. You entered {welcomemsgreply.content}."))
                    continue
                else:
                    welcomemessage, errors = utils.do_template(welcomemsgreply.content, owner, guild)
                    if errors:
                        if welcomemessage.startswith("[") and welcomemessage.endswith("]"):
                            embed = discord.Embed(colour=guild.me.colour, description=welcomemessage[1:-1].format(user=owner.mention))
                            embed.add_field(name='Warning', value='The following could not be found:\n{}').format('\n'.join(errors))
                            await owner.send(embed=embed)
                        else:
                            await owner.send("{msg}\n\n**Warning:**\nThe following could not be found: {errors}").format(msg=welcomemessage, errors=', '.join(errors))
                        await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description="Please check the data given and retry a new welcome message, or reply with **N** to use the default."))
                        continue
                    else:
                        if welcomemessage.startswith("[") and welcomemessage.endswith("]"):
                            embed = discord.Embed(colour=guild.me.colour, description=welcomemessage[1:-1].format(user=owner.mention))
                            question = await owner.send(content="Here's what you sent. Does it look ok?",embed=embed)
                            try:
                                timeout = False
                                res, reactuser = await utils.ask(Dobby, question, owner.id)
                            except TypeError:
                                timeout = True
                        else:
                            question = await owner.send(content="Here's what you sent. Does it look ok?\n\n{welcome}").format(welcome=welcomemessage.format(user=owner.mention))
                            try:
                                timeout = False
                                res, reactuser = await utils.ask(Dobby, question, owner)
                            except TypeError:
                                timeout = True
                        if timeout or res.emoji == '❎':
                            await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description="Please enter a new welcome message, or reply with **N** to use the default."))
                            continue
                        else:
                            config_dict_temp['welcome']['welcomemsg'] = welcomemessage
                            await owner.send(embed=discord.Embed(colour=discord.Colour.green(), description="Welcome Message set to:\n\n{}".format(config_dict_temp['welcome']['welcomemsg'])))
                            break
                break
            await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description="Which channel in your server would you like me to post the Welcome Messages? You can also choose to have them sent to the new member via Direct Message (DM) instead.\n\nRespond with: **channel-name** or ID of a channel in your server or **DM** to Direct Message:").set_author(name="Welcome Message Channel", icon_url=Dobby.user.avatar_url))
            while True:
                welcomechannelreply = await Dobby.wait_for('message',check=lambda message: message.guild == None and message.author == owner)
                if welcomechannelreply.content.lower() == "dm":
                    config_dict_temp['welcome']['welcomechan'] = "dm"
                    await owner.send(embed=discord.Embed(colour=discord.Colour.green(), description="Welcome DM set"))
                    break
                elif " " in welcomechannelreply.content.lower():
                    await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description="Channel names can't contain spaces, sorry. Please double check the name and send your response again."))
                    continue
                elif welcomechannelreply.content.lower() == "cancel":
                    await owner.send(embed=discord.Embed(colour=discord.Colour.red(), description='**CONFIG CANCELLED!**\n\nNo changes have been made.'))
                    return None
                else:
                    item = welcomechannelreply.content
                    channel = None
                    if item.isdigit():
                        channel = discord.utils.get(guild.text_channels, id=int(item))
                    if not channel:
                        item = re.sub('[^a-zA-Z0-9 _\\-]+', '', item)
                        item = item.replace(" ","-")
                        name = await letter_case(guild.text_channels, item.lower())
                        channel = discord.utils.get(guild.text_channels, name=name)
                    if channel:
                        guild_channel_list = []
                        for textchannel in guild.text_channels:
                            guild_channel_list.append(textchannel.id)
                        diff = set([channel.id]) - set(guild_channel_list)
                    else:
                        diff = True
                    if (not diff):
                        config_dict_temp['welcome']['welcomechan'] = channel.id
                        ow = channel.overwrites_for(Dobby.user)
                        ow.send_messages = True
                        ow.read_messages = True
                        ow.manage_roles = True
                        try:
                            await channel.set_permissions(Dobby.user, overwrite = ow)
                        except (discord.errors.Forbidden, discord.errors.HTTPException, discord.errors.InvalidArgument):
                            await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description=f"I couldn't set my own permissions in this channel. Please ensure I have the correct permissions in {channel.mention} using **{ctx.prefix}get perms**."))
                        await owner.send(embed=discord.Embed(colour=discord.Colour.green(), description=f'Welcome Channel set to {welcomechannelreply.content.lower()}'))
                        break
                    else:
                        await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description="The channel you provided isn't in your server. Please double check your channel and resend your response."))
                        continue
                break
            break
        elif welcomereply.content.lower() == 'n':
            config_dict_temp['welcome']['enabled'] = False
            await owner.send(embed=discord.Embed(colour=discord.Colour.red(), description='Welcome Message disabled!'))
            break
        elif welcomereply.content.lower() == 'cancel':
            await owner.send(embed=discord.Embed(colour=discord.Colour.red(), description='**CONFIG CANCELLED!**\n\nNo changes have been made.'))
            return None
        else:
            await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description="I'm sorry I don't understand. Please reply with either **N** to disable, or **Y** to enable."))
            continue
    ctx.config_dict_temp = config_dict_temp
    return ctx

async def _configure_regions(ctx, Dobby):
    guild_dict = Dobby.guild_dict
    guild = ctx.message.guild
    owner = ctx.message.author
    config_dict_temp = getattr(ctx, 'config_dict_temp',copy.deepcopy(guild_dict[guild.id]['configure_dict']))
    config_dict_temp.setdefault('regions', {})
    await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description="I can keep track of multiple regions within your community. This can be useful for communities that span multiple cities. To start, I'll need the names of the regions you'd like to set up: `region-name, region-name, region-name`\n\nExample: `north-saffron, south-saffron, celadon`\n\nTo facilitate communication, I will be creating roles for each region name provided, so make sure the names are meaningful!\n\nIf you do not require regions, you may want to disable this functionality.\n\nRespond with: **N** to disable, or the **region-name** list to enable, each seperated with a comma and space:").set_author(name='Region Names', icon_url=Dobby.user.avatar_url))
    region_dict = {}
    while True:
        region_names = await Dobby.wait_for('message', check=(lambda message: (message.guild == None) and message.author == owner))
        response = region_names.content.strip().lower()
        if response == 'n':
            config_dict_temp['regions']['enabled'] = False
            await owner.send(embed=discord.Embed(colour=discord.Colour.red(), description='Regions disabled'))
            break
        elif response == 'cancel':
            await owner.send(embed=discord.Embed(colour=discord.Colour.red(), description='**CONFIG CANCELLED!**\n\nNo changes have been made.'))
            return None
        else:
            config_dict_temp['regions']['enabled'] = True
            region_names_list = re.split(r'\s*,\s*', response)
        break
    if config_dict_temp['regions']['enabled']:
        await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description='Occasionally I will generate Google Maps links to give people directions to locations! To do this, I need to know what city/town/area each region represents to ensure I get the right location in the map. For each region name you provided, I will need its corresponding general location using only letters and spaces, with each location seperated by a comma and space.\n\nExample: `saffron city kanto, saffron city kanto, celadon city kanto`\n\nEach location will have to be in the same order as you provided the names in the previous question.\n\nRespond with: **location info, location info, location info** each matching the order of the previous region name list below.').set_author(name='Region Locations', icon_url=Dobby.user.avatar_url))
        await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description='{region_name_list}'.format(region_name_list=response[:2000])).set_author(name='Entered Regions', icon_url=Dobby.user.avatar_url))
        while True:
            locations = await Dobby.wait_for('message', check=(lambda message: (message.guild == None) and message.author == owner))
            response = locations.content.strip().lower()
            if response == 'cancel':
                await owner.send(embed=discord.Embed(colour=discord.Colour.red(), description='**CONFIG CANCELLED!**\n\nNo changes have been made.'))
                return None
            region_locations_list = re.split(r'\s*,\s*', response)
            if len(region_locations_list) == len(region_names_list):
                for i in range(len(region_names_list)):
                    region_dict[region_names_list[i]] = {'location': region_locations_list[i], 'role': utils.sanitize_channel_name(region_names_list[i])}
                break
            else:
                await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description="The number of locations doesn't match the number of regions you gave me earlier!\n\nI'll show you the two lists to compare:\n\n{region_names_list}\n{region_locations_list}\n\nPlease double check that your locations match up with your provided region names and resend your response.".format(region_names_list=', '.join(region_names_list), region_locations_list=', '.join(region_locations_list))))
                continue
        await owner.send(embed=discord.Embed(colour=discord.Colour.green(), description='Region locations are set'))
        await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description='Lastly, I need to know what channels should be flagged to allow users to modify their region assignments. Please enter the channels to be used for this as a comma-separated list. \n\nExample: `general, region-assignment`\n\nNote that this answer does *not* directly correspond to the previously entered channels/regions.\n\n').set_author(name='Region Command Channels', icon_url=Dobby.user.avatar_url))
        while True:
            locations = await Dobby.wait_for('message', check=(lambda message: (message.guild == None) and message.author == owner))
            response = locations.content.strip().lower()
            if response == 'cancel':
                await owner.send(embed=discord.Embed(colour=discord.Colour.red(), description='**CONFIG CANCELLED!**\n\nNo changes have been made.'))
                return None
            channel_list = [c.strip() for c in response.split(',')]
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
                await owner.send(embed=discord.Embed(colour=discord.Colour.green(), description='Region Command Channels enabled'))
                for channel in channel_objs:
                    ow = channel.overwrites_for(Dobby.user)
                    ow.send_messages = True
                    ow.read_messages = True
                    ow.manage_roles = True
                    try:
                        await channel.set_permissions(Dobby.user, overwrite=ow)
                    except (discord.errors.Forbidden, discord.errors.HTTPException, discord.errors.InvalidArgument):
                        await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description='I couldn\'t set my own permissions in this channel. Please ensure I have the correct permissions in {channel} using **{prefix}get perms**.'.format(prefix=ctx.prefix, channel=channel.mention)))
                config_dict_temp['regions']['command_channels'] = channel_list
                break
            else:
                await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description="The channel list you provided doesn't match with your servers channels.\n\nThe following aren't in your server: **{invalid_channels}**\n\nPlease double check your channel list and resend your reponse.".format(invalid_channels=', '.join(channel_errors))))
                continue
    # set up roles
    new_region_roles = set([r['role'] for r in region_dict.values()])
    existing_region_dict = config_dict_temp['regions'].get('info', None)
    if existing_region_dict:
        existing_region_roles = set([r['role'] for r in existing_region_dict.values()])
        obsolete_roles = existing_region_roles - new_region_roles
        new_region_roles = new_region_roles - existing_region_roles
        # remove obsolete roles
        for role in obsolete_roles:
            temp_role = discord.utils.get(guild.roles, name=role)
            if temp_role:
                try:
                    await temp_role.delete(reason="Removed from region configuration")
                except discord.errors.HTTPException:
                    pass
        # remove obsolete roles
        for role in obsolete_roles:
            temp_role = discord.utils.get(guild.roles, name=role)
            if temp_role:
                try:
                    await temp_role.delete(reason="Removed from region configuration")
                except discord.errors.HTTPException:
                    pass
    for role in new_region_roles:
        temp_role = discord.utils.get(guild.roles, name=role)
        if not temp_role:
            try:
                await guild.create_role(name=role, hoist=False, mentionable=True)
            except discord.errors.HTTPException:
                pass
    await owner.send(embed=discord.Embed(colour=discord.Colour.green(), description='Region roles updated'))
    config_dict_temp['regions']['info'] = region_dict
    ctx.config_dict_temp = config_dict_temp
    return ctx

async def _configure_join(ctx, Dobby):
    guild_dict = Dobby.guild_dict
    guild = ctx.message.guild
    owner = ctx.message.author
    config_dict_temp = getattr(ctx, 'config_dict_temp',copy.deepcopy(guild_dict[guild.id]['configure_dict']))
    if 'join' not in config_dict_temp:
        config_dict_temp['join'] = {'enabled': False, 'link': ''}
    await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description="The **!join** command allows your users to get an invite link to your server \
even if they are otherwise prevented from generating invite links.\n\nIf you would like to enable this, please provide a non-expiring invite link to your server.\
If you would like to disable this feature, reply with **N**. To cancel this configuration session, reply with **cancel**.\
").set_author(name='Join Link Configuration', icon_url=Dobby.user.avatar_url))
    while True:
        joinmsg = await Dobby.wait_for('message', check=(lambda message: (message.guild == None) and message.author == owner))
        if joinmsg.content.lower() == 'cancel':
            await owner.send(embed=discord.Embed(colour=discord.Colour.red(), description='**CONFIG CANCELLED!**\n\nNo changes have been made.'))
            return None
        elif joinmsg.content.lower() == 'n':
            config_dict_temp['join'] = {'enabled': False, 'link': ''}
            await owner.send(embed=discord.Embed(colour=discord.Colour.red(), description='Invite link disabled.'))
            break
        else:
            if 'discord.gg/' in joinmsg.content.lower() or 'discordapp.com/invite/' in joinmsg.content.lower():
                config_dict_temp['join'] = {'enabled': True, 'link': joinmsg.content}
                break
            else:
                await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description='That does not appear to be a valid invite link. Please try again.'))
    ctx.config_dict_temp = config_dict_temp
    return ctx

async def _configure_settings(ctx, Dobby):
    guild_dict = Dobby.guild_dict
    guild = ctx.message.guild
    owner = ctx.message.author
    config_dict_temp = getattr(ctx, 'config_dict_temp',copy.deepcopy(guild_dict[guild.id]['configure_dict']))
    await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description="There are a few settings available that are not within **!configure**. \
        To set these, use **!set <setting>** in any channel to set that setting.\n\nThese include:\n\
        **!set prefix <prefix>** - To set my command prefix\n\
        **!set timezone <offset>** - To set offset outside of **!configure**\n\n\
        However, we can set your timezone now to help coordinate reports or we can setup an admin command channel. \
        For others, use the **!set** command.\n\nThe current 24-hr time UTC is {utctime}. \
        Reply with 'skip' to setup your admin command channels.\
        How many hours off from that are you?\n\nRespond with: A number from **-12** to **12**:"\
        .format(utctime=strftime('%H:%M', time.gmtime()))).set_author(name='Timezone Configuration and Other Settings', icon_url=Dobby.user.avatar_url))
    skipped = False
    while True:
        offsetmsg = await Dobby.wait_for('message', check=(lambda message: (message.guild == None) and message.author == owner))
        if offsetmsg.content.lower() == 'cancel':
            await owner.send(embed=discord.Embed(colour=discord.Colour.red(), description='**CONFIG CANCELLED!**\n\nNo changes have been made.'))
            return None
        elif offsetmsg.content.lower() == 'skip':
            await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description='Timezone configuration skipped.'))
            skipped = True
            break
        else:
            try:
                offset = float(offsetmsg.content)
            except ValueError:
                await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description="I couldn't convert your answer to an appropriate timezone!\n\n\
                    Please double check what you sent me and resend a number from **-12** to **12**."))
                continue
            if (not ((- 12) <= offset <= 14)):
                await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description="I couldn't convert your answer to an appropriate timezone!\n\n\
                    Please double check what you sent me and resend a number from **-12** to **12**."))
                continue
            else:
                break
    if not skipped:
        config_dict_temp['settings']['offset'] = offset
        await owner.send(embed=discord.Embed(colour=discord.Colour.green(), description='Timezone set'))
    else:
        await owner.send(embed=discord.Embed(colour=discord.Colour.lighter_grey(), description="It may be helpful to have an admin only command channel for\
            interacting with Dobby.\n\nPlease provide a channel name or id for this purpose.\nYou can also provide a comma separate list but all list\
            items should be the same (all names or all ids)."))
        while True:
            channel_message = await Dobby.wait_for('message', check=(lambda message: (message.guild == None) and message.author == owner))
            if offsetmsg.content.lower() == 'cancel':
                await owner.send(embed=discord.Embed(colour=discord.Colour.red(), description='**CONFIG CANCELLED!**\n\nNo changes have been made.'))
                return None
            else:
                adminchannel_list = channel_message.content.lower().split(',')
                adminchannel_list = [x.strip() for x in adminchannel_list]
                guild_channel_list = []
                for channel in guild.text_channels:
                    guild_channel_list.append(channel.id)
                adminchannel_objs = []
                adminchannel_names = []
                adminchannel_errors = []
                for item in adminchannel_list:
                    channel = None
                    if item.isdigit():
                        channel = discord.utils.get(guild.text_channels, id=int(item))
                    if not channel:
                        item = re.sub('[^a-zA-Z0-9 _\\-]+', '', item)
                        item = item.replace(" ","-")
                        name = await letter_case(guild.text_channels, item.lower())
                        channel = discord.utils.get(guild.text_channels, name=name)
                    if channel:
                        adminchannel_objs.append(channel)
                        adminchannel_names.append(channel.name)
                    else:
                        adminchannel_errors.append(item)
                adminchannel_list = [x.id for x in adminchannel_objs]
                diff = set(adminchannel_list) - set(guild_channel_list)
                if (not diff) and (not adminchannel_errors):
                    for channel in adminchannel_objs:
                        ow = channel.overwrites_for(Dobby.user)
                        ow.send_messages = True
                        ow.read_messages = True
                        ow.manage_roles = True
                        try:
                            await channel.set_permissions(Dobby.user, overwrite = ow)
                        except (discord.errors.Forbidden, discord.errors.HTTPException, discord.errors.InvalidArgument):
                            await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description='I couldn\'t set my own permissions in this channel. Please ensure I have the correct permissions in {channel} using **{prefix}get perms**.'.format(prefix=ctx.prefix, channel=channel.mention)))
                    break
                else:
                    await owner.send(embed=discord.Embed(colour=discord.Colour.orange(), description="The channel list you provided doesn't match with your servers channels.\n\nThe following aren't in your server: **{invalid_channels}**\n\nPlease double check your channel list and resend your reponse.".format(invalid_channels=', '.join(adminchannel_errors))))
                    continue
        command_channels = []
        for channel in adminchannel_objs:
            command_channels.append(channel.id)
        admin_dict = config_dict_temp.setdefault('admin',{})
        admin_dict['command_channels'] = command_channels
    await owner.send(embed=discord.Embed(colour=discord.Colour.green(), description='Admin Command Channels enabled'))
    ctx.config_dict_temp = config_dict_temp
    return ctx
