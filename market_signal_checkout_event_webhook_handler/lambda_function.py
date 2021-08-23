import datetime, decimal, os
import json
import stripe

stripe.api_key = os.getenv('STRIPE_SECRET_KEY') 

_STRIPE_WEBHOOK_ENDPOINT_SECRET = os.getenv('STRIPE_WEBHOOK_ENDPOINT_SECRET') 
_EVENT_KEY_PATH_PARAMETER = 'pathParameters'
_EVENT_KEY_QUERY_STRING_PARAMETER = 'queryStringParameters'
_EVENT_KEY_HTTP_METHOD = 'httpMethod'
_EVENT_KEY_BODY = 'body'
_EVENT_KEY_HEADERS = 'headers'


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

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return int(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.strftime(_DATETIME_FORMAT)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

def lambda_handler(event, context):
    print('event:', event)
    query_string_parameters = event[_EVENT_KEY_QUERY_STRING_PARAMETER]
    print("query_string_parameters:", query_string_parameters)

    if _EVENT_KEY_BODY not in event:
        res = _RESPONSE_400
        res['body'] = json.dumps('event body is not found.')
        return res

    body = event[_EVENT_KEY_BODY]
    if body is None:
        res = _RESPONSE_400
        res['body'] = json.dumps('request body is not found.')
        return res

    json_body = json.loads(body)
    print('json body:', json_body)

    headers = None
    if _EVENT_KEY_HEADERS in event:
        headers = event[_EVENT_KEY_HEADERS]
    if not headers:
        res = _RESPONSE_400
        res['body'] = json.dumps('request header is empty.'.format(alert_id=alert_id))
        return res

    sig_header = headers['Stripe-Signature'];
    stripe_event = None

    try:
        stripe_event = stripe.Webhook.construct_event(
          body, sig_header, _STRIPE_WEBHOOK_ENDPOINT_SECRET
        )
    except ValueError as e:
        res = _RESPONSE_400
        res['body'] = json.dumps('Invalid payload.')
        return res
    except stripe.error.SignatureVerificationError as e:
        res = _RESPONSE_400
        res['body'] = json.dumps('Invalid signature.')
        return res

    if json_body['type'] == "customer.subscription.created":
        print('customer.subscription.created')
        items = json_body['data']['object']['items']['data']
        for item in items:
            print('item', item)
            price_id = item['price']['id']
            pass

    result = {}

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': json.dumps(result, cls=DecimalEncoder)
    }


