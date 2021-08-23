import datetime, decimal, os
import json
import authorize
import stripe

stripe.api_key = os.getenv('STRIPE_SECRET_KEY') 

_EVENT_KEY_PATH_PARAMETER = 'pathParameters'
_EVENT_KEY_QUERY_STRING_PARAMETER = 'queryStringParameters'
_EVENT_KEY_HTTP_METHOD = 'httpMethod'
_CALLBACK_URL = 'callback_url'
_PARAM_KEY_CUSTOMER_ID = 'customer_id'


_RESPONSE_303 = {
        'statusCode': 303,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        }
    }

_RESPONSE_400 = {
        'statusCode': 400,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        }
    }

_RESPONSE_403 = {
        'statusCode': 403,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        }
    }


_RESPONSE_500 = {
        'statusCode': 500,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        }
    }


def get_portal_url(stripe_customer_id, callback_url):
    try:
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=callback_url,
        )
        return session.url
    except Exception as ex:
        print(ex)
        return None


def lambda_handler(event, context):
    print('event:', event)
    authed = authorize.is_authorized(event)
    if not authed:
        print('returning 403 as not authed.')
        return _RESPONSE_403

    query_string_parameters = event[_EVENT_KEY_QUERY_STRING_PARAMETER]
    print("query_string_parameters:", query_string_parameters)

    http_method = 'GET'
    if _EVENT_KEY_HTTP_METHOD in event:
        http_method = event[_EVENT_KEY_HTTP_METHOD]

    if http_method != 'POST':
        print('returning 400 as the method {m} is not POST.'.format(m = http_method))
        return _RESPONSE_400

    stripe_customer_id = None
    if query_string_parameters:
        if _PARAM_KEY_CUSTOMER_ID in query_string_parameters:
            stripe_customer_id = query_string_parameters[_PARAM_KEY_CUSTOMER_ID]
    if stripe_customer_id is None:
        print('returning 400 as the method customer id is not provided.')
        return _RESPONSE_400

    callback_url = None
    if query_string_parameters:
        if _CALLBACK_URL in query_string_parameters:
            callback_url = query_string_parameters[_CALLBACK_URL]
    if callback_url is None:
        print('returning 400 as the method callback url is not provided.')
        return _RESPONSE_400

    redirect_url = get_portal_url(stripe_customer_id, callback_url)
    if not redirect_url:
        print('could not retrieve the portal url.')
        return _RESPONSE_500

    ret = _RESPONSE_303
    ret['headers']['Location'] = redirect_url
    ret['headers']['Access-Control-Allow-Origin'] = '*'
    #return ret

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': json.dumps(redirect_url)
    }
