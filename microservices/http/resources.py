from addict import Dict


class Resource(dict):
    def __init__(self, **kwargs):
        super(Resource, self).__init__(**kwargs)


class ResourceInfo(dict):
    def __init__(self, resource, update=None, **kwargs):
        super(ResourceInfo, self).__init__()
        self.data = Dict()
        self['resource'] = resource
        if kwargs:
            self['methods'] = kwargs
        if update is not None:
            self.update(update)