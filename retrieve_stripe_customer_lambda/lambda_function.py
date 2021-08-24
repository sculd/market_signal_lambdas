import json, requests, stripe, os
import datetime, decimal
import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
import authorize

_EVENT_KEY_PATH_PARAMETER = 'pathParameters'
_EVENT_KEY_QUERY_STRING_PARAMETER = 'queryStringParameters'
_EVENT_KEY_HTTP_METHOD = 'httpMethod'
_EVENT_KEY_BODY = 'body'
_PATH_PARAMETER_USER = 'user'
_PARAM_KEY_EMAIL = 'email'
_RESOURCE_DYNAMODB = 'dynamodb'
_TABLE_NAME = 'subscription'
_DATABASE_KEY_AUTH0_USER_ID = 'auth0_user_id'
_DATABASE_KEY_STRIPE_CUSTOMER_ID = 'stripe_customer_id'
_DATABASE_KEY_IS_ACTIVE = 'is_active'

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

stripe.api_key = os.getenv('STRIPE_SECRET_KEY') 


def create_stripe_customer(email, auth0_user_id):
    c = stripe.Customer.create(
      description="This is a customer created for an auth0 account.",
      email=email,
      metadata={
        'auth0_user_id': auth0_user_id
      }
    )

    return c['id']


def get_stripe_customer_item_for_auth0_user(auth0_user_id):
    dynamodb = boto3.resource(_RESOURCE_DYNAMODB)
    table = dynamodb.Table(_TABLE_NAME)
    response = table.query(
        KeyConditionExpression=Key(_DATABASE_KEY_AUTH0_USER_ID).eq(auth0_user_id)
    )
    items = response['Items']
    if len(items) == 0:
      return None

    if len(items) > 1:
      print('something is wrong. There are {n} entryes for auth0 user {u}'.format(n=len(items), u =auth0_user_id))
    return items[0]


def update_stripe_customer_item_for_auth0_user(auth0_user_id, stripe_customer_id):
    dynamodb = boto3.resource(_RESOURCE_DYNAMODB)
    table = dynamodb.Table(_TABLE_NAME)

    item = {
      _DATABASE_KEY_AUTH0_USER_ID: auth0_user_id,
      _DATABASE_KEY_STRIPE_CUSTOMER_ID: stripe_customer_id,
      _DATABASE_KEY_IS_ACTIVE: False
    }
    try:
        table.put_item(
            Item=item
        )
    except Exception as ex:
        print(ex)
    print('updated the stripe customer {c} for auth0 user {u}'.format(c=stripe_customer_id, u=auth0_user_id))


def retrieve_stripe_customer_subscription(stripe_customer_id):
  c = stripe.Customer.retrieve(stripe_customer_id)
  print('c:', c)
  return c['subscriptions'] if 'subscriptions' in c else {}


def lambda_handler(event, context):
    print('event:', event)
    path_parameters = event[_EVENT_KEY_PATH_PARAMETER]
    if _PATH_PARAMETER_USER not in path_parameters:
        res = _RESPONSE_400
        res['body'] = json.dumps('user is not specified.')
        return res

    user_id = path_parameters[_PATH_PARAMETER_USER]
    if not user_id:
        res = _RESPONSE_400
        res['body'] = json.dumps('user id is not valid.')
        return res

    authed = authorize.is_authorized(event, user_id)
    if not authed:
        print('returning 403 as not authed.')
        return _RESPONSE_403

    if _EVENT_KEY_HTTP_METHOD not in event:
        res = _RESPONSE_400
        res['body'] = json.dumps('http method is not found.')
        return res

    if event[_EVENT_KEY_HTTP_METHOD] != 'GET':
        res = _RESPONSE_400
        res['body'] = json.dumps('wrong http method.')
        return res

    if _EVENT_KEY_QUERY_STRING_PARAMETER not in event:
        res = _RESPONSE_400
        res['body'] = json.dumps('no query parameter is found.')
        return res

    query_string_parameters = event[_EVENT_KEY_QUERY_STRING_PARAMETER]
    if query_string_parameters is None or _PARAM_KEY_EMAIL not in query_string_parameters:
        res = _RESPONSE_400
        res['body'] = json.dumps('email query parameter is not found.')
        return res

    stripe_customer_item = get_stripe_customer_item_for_auth0_user(user_id)
    if not stripe_customer_item:
        email = query_string_parameters[_PARAM_KEY_EMAIL]
        stripe_customer_id = create_stripe_customer(email, user_id)
        update_stripe_customer_item_for_auth0_user(user_id, stripe_customer_id)

    stripe_customer_item = get_stripe_customer_item_for_auth0_user(user_id)
    print('stripe_customer_item:', stripe_customer_item)
    r_body = stripe_customer_item
    r_body['subscriptions'] = retrieve_stripe_customer_subscription(stripe_customer_item['id'])

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': json.dumps(r_body)
    }
