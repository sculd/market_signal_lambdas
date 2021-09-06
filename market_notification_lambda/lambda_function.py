import datetime, decimal, stripe, os
import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
import pytz
import report_email, report_sms

stripe.api_key = os.getenv('STRIPE_SECRET_KEY') 

_TIMEZONE_US_EAST = pytz.timezone('US/EASTERN')

_RESOURCE_DYNAMODB = 'dynamodb'
_TABLE_NAME_ALERTS = 'alerts'
_TABLE_NAME_SUBSCRIPTION = 'subscription'

_EVENT_KEY_QUERY_STRING_PARAMETER = 'queryStringParameters'
_EVENT_KEY_BODY = 'body'

_PARAM_KEY_SYMBOL = 'symbol'
_PARAM_KEY_CURRENT_PRICE = 'current_price'
_PARAM_KEY_EPOCH = 'epoch'
_PARAM_KEY_MIN_DROP_PERCENT = 'min_drop_percent'
_PARAM_KEY_PRICE_AT_MIN_DROP = 'price_at_min_drop'
_PARAM_KEY_EPOCH_AT_MIN_DROP = 'epoch_at_min_drop'
_PARAM_KEY_MAX_JUMP_PERCENT = 'max_jump_percent'
_PARAM_KEY_PRICE_AT_MAX_JUMP = 'price_at_max_jump'
_PARAM_KEY_EPOCH_AT_MAX_JUMP = 'epoch_at_max_jump'
_PARAM_KEY_WINDOW_SIZE_MINUTES = 'window_size_minutes'
_PARAM_KEY_THRESHOLD_PERCENT = 'threshold_percent'
_PARAM_KEY_MOVE_TYPE = 'move_type'

_DATABASE_KEY_SYMBOL = 'symbol'
_DATABASE_KEY_WINDOW_SIZE_MINUTES = 'window_size_minutes'
_DATABASE_KEY_THRESHOLD_PERCENT = 'threshold_percent'
_DATABASE_KEY_MOVE_TYPE = 'move_type'
_DATABASE_KEY_AUTH0_USER_ID = 'auth0_user_id'


_RESPONSE_400 = {
        'statusCode': 400,
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


def _get_alert_items(symbol, window_minutes, threshold_percent, move_type):
    move_type = move_type.lower()
    dynamodb = boto3.resource(_RESOURCE_DYNAMODB)
    table = dynamodb.Table(_TABLE_NAME_ALERTS)

    response = table.query(
        IndexName='symbol-index',
        KeyConditionExpression=Key(_DATABASE_KEY_SYMBOL).eq(symbol),
        FilterExpression=Attr(_DATABASE_KEY_THRESHOLD_PERCENT).eq(threshold_percent) & Attr(_DATABASE_KEY_WINDOW_SIZE_MINUTES).eq(window_minutes) & Attr(_DATABASE_KEY_MOVE_TYPE).eq(move_type)
    )

    items = response['Items']
    return items


def _get_alert_any_symbol_items(window_minutes, threshold_percent, move_type):
    move_type = move_type.lower()
    dynamodb = boto3.resource(_RESOURCE_DYNAMODB)
    table = dynamodb.Table(_TABLE_NAME_ALERTS)

    response = table.query(
        IndexName='symbol-index',
        KeyConditionExpression=Key(_DATABASE_KEY_SYMBOL).eq('*'),
        FilterExpression=Attr(_DATABASE_KEY_THRESHOLD_PERCENT).eq(threshold_percent) & Attr(_DATABASE_KEY_WINDOW_SIZE_MINUTES).eq(window_minutes) & Attr(_DATABASE_KEY_MOVE_TYPE).eq(move_type)
    )

    items = response['Items']
    return items

def get_stripe_customer_item_for_auth0_user(auth0_user_id):
    dynamodb = boto3.resource(_RESOURCE_DYNAMODB)
    table = dynamodb.Table(_TABLE_NAME_SUBSCRIPTION)
    response = table.query(
        KeyConditionExpression=Key(_DATABASE_KEY_AUTH0_USER_ID).eq(auth0_user_id)
    )
    items = response['Items']
    if len(items) == 0:
      return None

    if len(items) > 1:
      print('something is wrong. There are {n} entryes for auth0 user {u}'.format(n=len(items), u =auth0_user_id))
      return {}
    return items[0]

def retrieve_stripe_customer_subscription(stripe_customer_id):
  c = stripe.Customer.retrieve(stripe_customer_id)
  return c['subscriptions'] if 'subscriptions' in c else {}

def is_paid_user(auth0_user_id):
    stripe_customer_item = get_stripe_customer_item_for_auth0_user(auth0_user_id)
    if not stripe_customer_item or 'stripe_customer_id' not in stripe_customer_item:
        print('stripe_customer_item_for_auth0_user is invalid')
        return False

    subscription = retrieve_stripe_customer_subscription(stripe_customer_item['stripe_customer_id'])
    if not subscription or 'data' not in subscription:
        print('subscription info not found for stripe_customer_id {c}'.format(c=stripe_customer_item['stripe_customer_id']))
        return False

    now_epoch = int(pytz.utc.localize(datetime.datetime.utcnow()).timestamp())
    for s in subscription['data']:
        s_dict = s.to_dict()
        if now_epoch <= s.current_period_end:
            metadata = s_dict['plan']['metadata'].to_dict()
            if 'tier' in metadata:
                if metadata['tier'] == 'light' or metadata['tier'] == 'premium':
                    print(metadata)
                    return True
    return False

def _filter_out_basic_tier_db_items(db_items):
    ret = []
    filter_out_cnt = 0
    for db_item in db_items:
        if not is_paid_user(db_item['user_id']):
            filter_out_cnt += 1
            continue
        ret.append(db_item)
    if filter_out_cnt > 0:
        print('{c} items were filtered out'.format(c=filter_out_cnt))
    return ret

def collect_emails(items):
    emails = [i['notification_email'] for i in items if i['notification_to_email']]
    return list(set(emails))


def collect_smses(items):
    smses = [i['notification_sms'] for i in items if i['notification_to_sms']]
    return list(set(smses))


def lambda_handler(event, context):
    print("event:", event)

    if _EVENT_KEY_BODY not in event:
        res = _RESPONSE_400
        res['body'] = json.dumps('event body is not found.'.format(alert_id=alert_id))
        return res

    body = event[_EVENT_KEY_BODY]
    if body is None:
        res = _RESPONSE_400
        res['body'] = json.dumps('request body is not found.'.format(alert_id=alert_id))
        return res

    print('body:', body)
    js_body = json.loads(body)
    print('json body:', js_body)

    keys = [_PARAM_KEY_SYMBOL, _PARAM_KEY_CURRENT_PRICE, _PARAM_KEY_EPOCH, 
            _PARAM_KEY_MIN_DROP_PERCENT, _PARAM_KEY_PRICE_AT_MIN_DROP, _PARAM_KEY_EPOCH_AT_MIN_DROP, 
            _PARAM_KEY_MAX_JUMP_PERCENT, _PARAM_KEY_PRICE_AT_MAX_JUMP, _PARAM_KEY_EPOCH_AT_MAX_JUMP, 
            _PARAM_KEY_WINDOW_SIZE_MINUTES, _PARAM_KEY_THRESHOLD_PERCENT, _PARAM_KEY_MOVE_TYPE]
    
    for key in keys:
        if key not in js_body:
            res = _RESPONSE_400
            res['body'] = json.dumps('body misses {key}.'.format(key=key))
            return res

    symbol = js_body[_PARAM_KEY_SYMBOL]
    current_price = js_body[_PARAM_KEY_CURRENT_PRICE]
    epoch = js_body[_PARAM_KEY_EPOCH]
    min_drop_percent = js_body[_PARAM_KEY_MIN_DROP_PERCENT]
    price_at_min_drop = js_body[_PARAM_KEY_PRICE_AT_MIN_DROP]
    epoch_at_min_drop = js_body[_PARAM_KEY_EPOCH_AT_MIN_DROP]
    max_jump_percent = js_body[_PARAM_KEY_MAX_JUMP_PERCENT]
    price_at_max_jump = js_body[_PARAM_KEY_PRICE_AT_MAX_JUMP]
    epoch_at_max_jump = js_body[_PARAM_KEY_EPOCH_AT_MAX_JUMP]
    window_minutes = js_body[_PARAM_KEY_WINDOW_SIZE_MINUTES]
    threshold_percent = js_body[_PARAM_KEY_THRESHOLD_PERCENT]
    move_type = js_body[_PARAM_KEY_MOVE_TYPE]

    items_matching_symbol = _get_alert_items(symbol, str(window_minutes), str(threshold_percent), move_type)
    items_any_symbol = _get_alert_any_symbol_items(str(window_minutes), str(threshold_percent), move_type)

    print('items_matching_symbol len: {l}'.format(l=len(items_matching_symbol)))
    print('items_any_symbol len: {l}'.format(l=len(items_any_symbol)))
    for i in items_matching_symbol: print('items_matching_symbol {i}'.format(i=i))
    for i in items_any_symbol: print('items_any_symbol {i}'.format(i=i))

    items = items_matching_symbol + items_any_symbol
    paid_items = _filter_out_basic_tier_db_items(items)
    emails = collect_emails(items)
    smses = collect_smses(paid_items)

    for email in emails:
        report_email.send_email_report(
            email,
            symbol, 
            current_price, int(epoch),
            min_drop_percent, price_at_min_drop, int(epoch_at_min_drop),
            max_jump_percent, price_at_max_jump, int(epoch_at_max_jump),
            window_minutes, threshold_percent, move_type)

    for sms in smses:
        report_sms.send_sms_report(
            sms,
            symbol, 
            current_price, int(epoch),
            min_drop_percent, price_at_min_drop, int(epoch_at_min_drop),
            max_jump_percent, price_at_max_jump, int(epoch_at_max_jump),
            window_minutes, threshold_percent, move_type)

    ret = {
        'emails': emails,
        'sms': smses
    }

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': json.dumps(ret, cls=DecimalEncoder)
    }
