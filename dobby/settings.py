class GuildConfig:
    def __init__(self, data):
        self._data = data
        self.prefix = self.settings['prefix']
        self.offset = self.settings['offset']
        self.has_configured = self.settings['done']

    @property
    def settings(self):
        return self._data['prefix']

class GuildData:
    def __init__(self, ctx, data):
        self.ctx = ctx
        self._data = data

    @property
    def config(self):
        return GuildConfig(self._data['configure_dict'])