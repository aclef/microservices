import urllib
import urlparse

import requests

from microservices.utils import get_logger


class ResponseError(Exception):
    def __init__(self, response, description, *args, **kwargs):
        self.response = response
        self.description = description
        self.status_code = response.status_code
        self.content = response.content
        super(ResponseError, self).__init__(*args, **kwargs)

    def __repr__(self):
        return 'Error status code: {}. Description: {}'.format(self.response.status_code, self.description)

    def __str__(self):
        return self.__repr__()

    def __unicode__(self):
        return self.__str__().decode()


class _client_request(object):
    def __init__(self, client, resources, method='get'):
        self.client = client
        self.resources = resources
        self.method = method
        self.logger = client.logger

    def __call__(self, *args, **kwargs):
        method = getattr(self.client, self.method)
        args = tuple(self.resources) + args
        return method(*args, **kwargs)


class _requests_method(object):
    def __init__(self, client, method):
        self.method = method
        self.client = client
        self.close_slash = client.close_slash
        self.logger = client.logger

    def build_resource(self, resources):
        resource = '/'.join(resources)
        self.logger.debug('Resource {} builded from {}'.format(resource, resources))
        return resource

    def __call__(self, *resources, **kwargs):
        response_key = kwargs.pop('response_key', None)
        key = kwargs.pop('key', None)
        if key is not None:
            response_key = key
        query = kwargs.pop('query', None)
        data = kwargs.pop('data', None)
        timeout = kwargs.pop('timeout', 60)
        resource = self.build_resource(resources)
        if data is not None:
            kwargs['json'] = data
        url = self.client.url_for(resource, query)
        self.logger.info('{}: {}'.format(self.method, url))
        response = requests.request(self.method, url, timeout=timeout, **kwargs)
        return self.client.handle_response(response, response_key=response_key)


class Resource(object):
    def __init__(self, client, resources):
        self.client = client
        self.resources = resources
        self.logger = client.logger

    def __getattr__(self, item):
        return _client_request(self.client, self.resources, item)

    def resource(self, *resources):
        resources = tuple(self.resources) + resources
        return Resource(self.client, resources)


class Client(object):
    ok_statuses = (200, 202,)
    to_none_statuses = (404,)

    def __init__(self, endpoint, ok_statuses=None, to_none_statuses=None, empty_to_none=True, close_slash=True,
                 logger=None):
        if logger is None:
            logger = get_logger(__name__)

        self.logger = logger
        if endpoint.endswith('/'):
            endpoint = endpoint[:-1]
        if ok_statuses is not None:
            self.ok_statuses = ok_statuses
        if to_none_statuses is not None:
            self.to_none_statuses = to_none_statuses
        self.empty_to_none = empty_to_none
        self.close_slash = close_slash
        parsed_url = urlparse.urlparse(endpoint)
        endpoint = self.get_endpoint_from_parsed_url(parsed_url)
        self.endpoint = endpoint
        self.path = parsed_url.path
        self.logger.debug('Client builded for endpoint {} and path {}'.format(self.endpoint, self.path))

    @staticmethod
    def get_endpoint_from_parsed_url(parsed_url):
        url_list = [(lambda: x if e < 2 else '')() for e, x in enumerate(list(parsed_url))]
        return urlparse.urlunparse(url_list)

    def url_for(self, resource='', query=None):
        parsed_url = list(urlparse.urlparse(self.endpoint))
        path = self.path + '/' + resource
        if self.close_slash:
            if not path.endswith('/'):
                path += '/'
        parsed_url[2] = path
        if query is not None:
            parsed_url[4] = urllib.urlencode(query, doseq=1)
        url = urlparse.urlunparse(parsed_url)
        self.logger.debug('Url {} builded for resource {}'.format(url, resource))
        return url

    def handle_response(self, response, response_key=None):
        status_code = response.status_code
        try:
            result = response.json()
        except Exception as e:
            raise ResponseError(response, str(e))

        if result:
            if response_key is not None and status_code in self.ok_statuses:
                if response_key in result:
                    result = result[response_key]
                else:
                    raise ResponseError(response, 'Response key not found!')
            elif response_key is not None and status_code in self.to_none_statuses:
                result = None
            elif status_code not in self.ok_statuses and status_code not in self.to_none_statuses:
                raise ResponseError(response, 'Status code {} not in ok_statuses {}'.format(status_code, self.ok_statuses))
        if response_key is not None and self.empty_to_none and result is not None and not result:
            result = None

        return result

    def __getattr__(self, item):
        return _requests_method(self, item)

    def resource(self, *resources):
        return Resource(self, resources)