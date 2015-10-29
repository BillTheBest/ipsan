# -*-coding: utf-8 -*-


# error code
EUSER_ALREADY_EXISTS = 200
EUSER_CREATE_USER = 201
EUSER_CANNOT_DELETE_ADMIN = 202

EHTTP_NO_CONTENT_TYPE = 301
EHTTP_INVALID_JSON_DATA = 302
EHTTP_UNSUPPORT_CONTENT_TYPE = 303


class APIError(Exception):

    def __init__(self, retcode, message=''):
        super(APIError, self).__init__(message)
        self.retcode = retcode
        self.message = message


class APIValueError(APIError):

    def __init__(self,  field):
        super(APIValueError, self).__init__(100, 'Field %s invalid' % field)


class APIAuthenticateError(APIError):

    def __init__(self):
        super(APIAuthenticateError, self).__init__(101, 'Authenticate error')


class APIResourceNotFoundError(APIError):

    def __init__(self, resource):
        super(APIResourceNotFoundError, self).__init__(
            102, 'Resource %s not found' % resource)
