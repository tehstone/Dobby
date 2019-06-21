import json
from peewee import Proxy, chunked
from playhouse.apsw_ext import *
from playhouse.sqlite_ext import JSONField
from playhouse.migrate import *

class DobbyDB:
    _db = Proxy()
    _migrator = None
    @classmethod
    def start(cls, db_path):
        handle = APSWDatabase(db_path, pragmas={
            'journal_mode': 'wal',
            'cache_size': -1 * 64000,
            'foreign_keys': 1,
            'ignore_check_constraints': 0
        })
        cls._db.initialize(handle)
        # ensure db matches current schema
        cls._db.create_tables([
            LocationTable, HouseTable, GuildTable, 
            WizardTable, RegionTable, LocationRegionRelation, 
            InnTable, GreenhouseTable, FortressTable,
            WizardReportRelation, LocationNoteTable
        ])
        cls.init()
        cls._migrator = SqliteMigrator(cls._db)

    @classmethod
    def stop(cls):
        return cls._db.close()
    
    @classmethod
    def init(cls):
        #check house
        try:
            HouseTable.get()
        except:
            HouseTable.reload_default()
        #check regions
        try:
            RegionTable.get()
        except:
            RegionTable.reload_default()
        #check locations
        try:
            LocationTable.get()
        except:
            LocationTable.reload_default()

class BaseModel(Model):
    class Meta:
        database = DobbyDB._db

class HouseTable(BaseModel):
    name = TextField(unique=True)
    emoji = TextField()

    @classmethod
    def reload_default(cls):
        if not DobbyDB._db:
            return
        try:
            cls.delete().execute()
        except:
            pass
        with open('config.json', 'r') as f:
            house_data = json.load(f)['house_dict']
        for name, emoji in house_data.items():
            cls.insert(name=name, emoji=emoji).execute()

class GuildTable(BaseModel):
    snowflake = BigIntegerField(unique=True)
    config_dict = JSONField(null=True)

class WizardTable(BaseModel):
    snowflake = BigIntegerField(index=True)
    house = ForeignKeyField(HouseTable, backref='wizards', null=True)
    guild = ForeignKeyField(GuildTable, field=GuildTable.snowflake, backref='wizards')

    class Meta:
        constraints = [SQL('UNIQUE(snowflake, guild_id)')]

class RegionTable(BaseModel):
    name = TextField(index=True)
    area = TextField(null=True)
    guild = ForeignKeyField(GuildTable, field=GuildTable.snowflake, backref='regions', index=True)

    @classmethod
    def reload_default(cls):
        if not DobbyDB._db:
            return
        try:
            cls.delete().execute()
        except:
            pass
        with open('data/region_data.json', 'r') as f:
            region_data = json.load(f)
        with DobbyDB._db.atomic():
            for region in region_data:
                try:
                    if 'guild' in region and region['guild']:
                        for guild_id in region['guild'].split(','):
                            guild, __ = GuildTable.get_or_create(snowflake=guild_id)
                            RegionTable.create(name=region['name'], area=None, guild=guild)
                except Exception as e:
                    import pdb; pdb.set_trace()
                    print(e)
    
    class Meta:
        constraints = [SQL('UNIQUE(name, guild_id)')]

class LocationTable(BaseModel):
    id = AutoField()
    name = TextField(index=True)
    latitude = TextField()
    longitude = TextField()
    guild = ForeignKeyField(GuildTable, field=GuildTable.snowflake, backref='locations', index=True)

    @classmethod
    def create_location(ctx, name, data, type):
        try:
            latitude, longitude = data['coordinates'].split(',')
            if 'guild' in data and data['guild']:
                for guild_id in data['guild'].split(','):
                    with DobbyDB._db.atomic():
                        guild, __ = GuildTable.get_or_create(snowflake=guild_id)
                        location = LocationTable.create(name=name, latitude=latitude, longitude=longitude, guild=guild)
                        if 'region' in data and data['region']:
                            for region_name in data['region'].split(','):
                                with DobbyDB._db.atomic():
                                    # guild_id used here because peewee will not get correctly if obj used and throw error
                                    region, __ = RegionTable.get_or_create(name=region_name, area=None, guild=guild_id)
                                    LocationRegionRelation.create(location=location, region=region)
                        if 'notes' in data:
                            for note in data['notes']:
                                LocationNoteTable.create(location=location, note=note)
                        if type == 'fortress':
                            FortressTable.create(location=location)
                        elif type == 'inn':
                            InnTable.create(location=location)
                        elif type == 'greenhouse':
                            GreenhouseTable.create(location=location)
        except Exception as e:
            import pdb; pdb.set_trace()
            print(e)

    @classmethod
    def reload_default(cls):
        if not DobbyDB._db:
            return
        try:
            cls.delete().execute()
        except:
            pass
        with open('data/fortress_data.json', 'r') as f:
            fortress_data = json.load(f)
        with open('data/inn_data.json', 'r') as f:
            inn_data = json.load(f)
        with open('data/greenhouse_data.json', 'r') as f:
            greenhouse_data = json.load(f)
        for name, data in fortress_data.items():
            LocationTable.create_location(name, data, 'fortress')
        for name, data in inn_data.items():
            LocationTable.create_location(name, data, 'inn')
        for name, data in greenhouse_data.items():
            LocationTable.create_location(name, data, 'greenhouse')

class LocationNoteTable(BaseModel):
    location = ForeignKeyField(LocationTable, backref='notes')
    note = TextField()

class LocationRegionRelation(BaseModel):
    location = ForeignKeyField(LocationTable, backref='regions')
    region = ForeignKeyField(RegionTable, backref='locations')

class InnTable(BaseModel):
    location = ForeignKeyField(LocationTable, backref='inns', primary_key=True)

class GreenhouseTable(BaseModel):
    location = ForeignKeyField(LocationTable, backref='greenhouses', primary_key=True)

class FortressTable(BaseModel):
    location = ForeignKeyField(LocationTable, backref='fortresses', primary_key=True)

class WizardReportRelation(BaseModel):
    id = AutoField()
    created = DateTimeField(index=True,formats=["%Y-%m-%d %H:%M:%s"])
    wizard = BigIntegerField(index=True)
    location = ForeignKeyField(LocationTable, index=True)
