import datetime
import json
import os
import tempfile

from discord.ext import commands

from dobby import utils, checks
from dobby.exts.db.dobbydb import *

class Location:
    def __init__(self, id, name, latitude, longitude, region, note):
        self.id = id
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.region = region
        if note is not None:
            self.note = note
    
    @property
    def coordinates(self):
        if self.latitude and self.longitude:
            return f"{self.latitude},{self.longitude}"
        return None
    
    @property
    def maps_url(self):
        if self.coordinates:
            query = self.coordinates
        else:
            query = self.name
            if self.region:
                query += f"+{'+'.join(self.region)}"
        return f"https://www.google.com/maps/search/?api=1&query={query}"

class Fortress(Location):
    __name__ = "Fortress"
    def __init__(self, id, name, latitude, longitude, region, ex_eligible, note):
        super().__init__(id, name, latitude, longitude, region, note)
        self.ex_eligible = ex_eligible

class Inn(Location):
    __name__ = "Inn"
    def __init__(self, id, name, latitude, longitude, region, note):
        super().__init__(id, name, latitude, longitude, region, note)

class Greenhouse(Location):
    __name__ = "Greenhouse"
    def __init__(self, id, name, latitude, longitude, region, note):
        super().__init__(id, name, latitude, longitude, region, note)

class LocationMatching(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_all(self, guild_id, regions=None):
        return self.get_fortresses(guild_id, regions=regions) + self.get_inns(guild_id, regions=regions) + self.get_greenhouses(guild_id, regions=regions)
    
    def get_fortresses(self, guild_id, regions=None):
        result = (FortressTable
                    .select(LocationTable.id,
                            LocationTable.name, 
                            LocationTable.latitude, 
                            LocationTable.longitude, 
                            RegionTable.name.alias('region'),
                            LocationNoteTable.note)
                    .join(LocationTable)
                    .join(LocationRegionRelation)
                    .join(RegionTable)
                    .join(LocationNoteTable, JOIN.LEFT_OUTER, on=(LocationNoteTable.location_id == LocationTable.id))
                    .where((LocationTable.guild == guild_id) &
                           (LocationTable.guild == RegionTable.guild)))
        if regions:
            if not isinstance(regions, list):
                regions = [regions]
            result = result.where(RegionTable.name << regions)
        result = result.objects(Fortress)
        return [o for o in result]

    def get_inns(self, guild_id, regions=None):
        result = (InnTable
                    .select(LocationTable.id,
                            LocationTable.name, 
                            LocationTable.latitude, 
                            LocationTable.longitude, 
                            RegionTable.name.alias('region'),
                            LocationNoteTable.note)
                    .join(LocationTable)
                    .join(LocationRegionRelation)
                    .join(RegionTable)
                    .join(LocationNoteTable, JOIN.LEFT_OUTER, on=(LocationNoteTable.location_id == LocationTable.id))
                    .where((LocationTable.guild == guild_id) &
                           (LocationTable.guild == RegionTable.guild)))
        if regions:
            if not isinstance(regions, list):
                regions = [regions]
            result = result.where(RegionTable.name << regions)
        result = result.objects(Inn)
        return [o for o in result]

    def get_greenhouses(self, guild_id, regions=None):
        result = (GreenhouseTable
                    .select(LocationTable.id,
                            LocationTable.name, 
                            LocationTable.latitude, 
                            LocationTable.longitude, 
                            RegionTable.name.alias('region'),
                            LocationNoteTable.note)
                    .join(LocationTable)
                    .join(LocationRegionRelation)
                    .join(RegionTable)
                    .join(LocationNoteTable, JOIN.LEFT_OUTER, on=(LocationNoteTable.location_id == LocationTable.id))
                    .where((LocationTable.guild == guild_id) &
                           (LocationTable.guild == RegionTable.guild)))
        if regions:
            if not isinstance(regions, list):
                regions = [regions]
            result = result.where(RegionTable.name << regions)
        result = result.objects(Greenhouse)
        return [o for o in result]

    def location_match(self, name, locations, threshold=75, isPartial=True, limit=None):
        match = utils.get_match([l.name for l in locations], name, threshold, isPartial, limit)
        if not isinstance(match, list):
            match = [match]
        return [(l, score) for l in locations for match_name, score in match if l.name == match_name]
    
    @commands.command(hidden=True, aliases=["lmt"])
    @commands.has_permissions(manage_guild=True)
    async def location_match_test(self, ctx, *, content=None):
        add_prefix = False
        if ',' not in content:
            return await ctx.send('Comma-separated type and name are required')
        loc_type, name, *regions = [c.strip() for c in content.split(',')]
        if not name or not loc_type:
            return await ctx.send('Type and name are required')
        loc_type = loc_type.lower()
        if 'inn' in loc_type:
            locations = self.get_inns(ctx.guild.id, regions)
        elif 'greenhouse' in loc_type:
            locations = self.get_greenhouses(ctx.guild.id, regions)
        elif loc_type.startswith('fortress'):
            locations = self.get_fortresses(ctx.guild.id, regions)
        else:
            add_prefix = True
            locations = self.get_all(ctx.guild.id, regions)
        if not locations:
            await ctx.send('Location matching has not been set up for this server.')
            return        
        result = self.location_match(name, locations)
        if not result:
            result = 'No matches found!'
        else:
            result = '\n'.join([f"{f'[{l.__name__}] ' if add_prefix else ''}{l.name} {score} ({l.latitude}, {l.longitude}) {l.region}" for l, score in result])
        for i in range(len(result) // 2001 + 1):
            await ctx.send(result[2001*i:2001*(i+1)])
    
    def _get_location_info_output(self, result, locations):
        match, score = result
        location_info = locations[match]
        coords = location_info['coordinates']
        notes = location_info.get('notes', 'No notes for this location.')
        location_info_str = (f"**Coordinates:** {coords}\n"
                        f"**Notes:** {notes}")
        return (f"Successful match with `{match}` "
                f"with a score of `{score}`\n{location_info_str}")

    def __process(self, type, locations):
        result = []
        for name, data in locations.items():
            coords = data['coordinates'].split(',')
            if type == "fortress":
                result.append(Fortress(name, coords[0], coords[1], None))
            elif type == "inn":
                result.append(Inn(name, coords[0], coords[1], None))
            elif type == "greenhouse":
                result.append(Greenhouse(name, coords[0], coords[1], None))
        return result

def setup(bot):
    bot.add_cog(LocationMatching(bot))
