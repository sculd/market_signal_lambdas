import datetime, decimal
import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
import pytz

_TIMEZONE_US_EAST = pytz.timezone('US/EASTERN')
_DATASET_ID_STOCK = 'market_data'
_DATASET_ID_BINANCE = 'market_data_binance'

_RESOURCE_DYNAMODB = 'dynamodb'
_TABLE_NAME = 'market_daily_stat'
_EVENT_KEY_QUERY_STRING_PARAMETER = 'queryStringParameters'
_PARAM_KEY_DATE_STR = 'date_str'
_PARAM_KEY_MARKET = 'market'
_PARAM_KEY_SYMBOL = 'symbol'
_DATABASE_KEY_SYMBOL = 'symbol'
_DATABASE_KEY_DATE_STR = 'date_str'
_DATABASE_KEY_MARKET = 'market'
_RESPONSE_KEY_DATE = 'date'
_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S%z'


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return int(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.strftime(_DATETIME_FORMAT)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


def dict_to_response(blob):
    return blob


def _get_now_et():
    return pytz.utc.localize(datetime.datetime.utcnow()).astimezone(_TIMEZONE_US_EAST)


def _get_today_date_str():
    return _get_now_et().strftime('%Y-%m-%d')


def _get_items(date_str, symbol, market):
    dynamodb = boto3.resource(_RESOURCE_DYNAMODB)
    table = dynamodb.Table(_TABLE_NAME)

    response = table.query(
        KeyConditionExpression=Key(_DATABASE_KEY_DATE_STR).eq(date_str) & Key(_DATABASE_KEY_SYMBOL).eq(symbol),
        FilterExpression=Attr(_DATABASE_KEY_MARKET).eq(market)
    )

    items = response['Items']
    items = [i for i in items if i[_DATABASE_KEY_MARKET] == market]
    return items


def lambda_handler(event, context):
    query_string_parameters = event[_EVENT_KEY_QUERY_STRING_PARAMETER]
    print("query_string_parameters:", query_string_parameters)
    market = 'stock'
    symbol = None
    date_strs = [_get_today_date_str()]
    prev_date = _get_now_et() - datetime.timedelta(days=1)
    while market == 'stock' and prev_date.weekday() >= 5:
        prev_date -= datetime.timedelta(days=1)
    date_strs.append(prev_date.strftime('%Y-%m-%d'))

    if query_string_parameters:
        if _PARAM_KEY_MARKET in query_string_parameters:
            market = query_string_parameters[_PARAM_KEY_MARKET]

        if _PARAM_KEY_SYMBOL in query_string_parameters:
            symbol = query_string_parameters[_PARAM_KEY_SYMBOL]

        if _PARAM_KEY_DATE_STR in query_string_parameters:
            date_strs = query_string_parameters[_PARAM_KEY_DATE_STR].split(',')

    print("symbol: {s}, market: {m}, date_str: {d}".format(s=symbol, m=market, d=','.join(date_strs)))

    items = []
    for date_str in date_strs:
        print('date_str:', date_str)
        items += _get_items(date_str, symbol, market)

    result = list(map(lambda blob: dict_to_response(blob), items))
    result = result[:30]

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': json.dumps(result, cls=DecimalEncoder)
    }
