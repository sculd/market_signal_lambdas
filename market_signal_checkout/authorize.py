import json, os
import requests
from authlib.jose import JsonWebToken

_EVENT_KEY_PATH_PARAMETER = 'pathParameters'
_PATH_PARAMETER_USER = 'user'
_EVENT_KEY_HEADERS = 'headers'
_HEADER_KEY_AUTHORIZATION = 'Authorization'
_APPLICATION_BASE_URL = os.getenv('AUTH0_APPLICATION_URL')
_JWKS_URL_PATH = '.well-known/jwks.json'
_AUDIENCE_URL_PATH = 'api/v2/'
_JWT = JsonWebToken(['RS256'])
_KEY_PREFIX = '-----BEGIN CERTIFICATE-----\n'
_KEY_POSTFIX = '\n-----END CERTIFICATE-----'

def _get_token_from_event(event):
    if _EVENT_KEY_HEADERS in event:
        headers = event[_EVENT_KEY_HEADERS]
        if headers and _HEADER_KEY_AUTHORIZATION in headers:
            return headers[_HEADER_KEY_AUTHORIZATION].split('Bearer ')[-1]

def _validate(event, key):
    encoded = _get_token_from_event(event)
    if encoded is None:
        print('not authed as the auth token is None')
        return False
    key_binary = key.encode('ascii')
    try:
        claims = _JWT.decode(encoded, key_binary)
        claims_option = {
            "iss": {
                "essential": True,
                "value": _APPLICATION_BASE_URL
            },
            "aud": {
                "essential": True,
                "values": [_APPLICATION_BASE_URL + _AUDIENCE_URL_PATH]
            }
        }
        claims.options = claims_option
        claims.validate()
    except Exception as ex:
        print('not authed as an exception happened:', ex)
        print(ex)
        return False

    return True

def _get_keys():
    url = _APPLICATION_BASE_URL + _JWKS_URL_PATH
    r = requests.get(url)
    if not r.ok:
        return []

    return [_KEY_PREFIX + k + _KEY_POSTFIX for ks in list(map(lambda k: k['x5c'], r.json()['keys'])) for k in ks]

def is_authorized(event):
    ks = _get_keys()
    for k in ks:
        if _validate(event, k):
            return True
    return False

