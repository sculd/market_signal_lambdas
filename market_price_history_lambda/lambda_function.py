import datetime, decimal, json
import os
import pytz
from binance.client import Client as BinanceClient
from polygon import RESTClient as PolygonClient


_TIMEZONE_US_EAST = pytz.timezone('US/EASTERN')
_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
_API_KEY = os.getenv('API_KEY_BINANCE')
_API_SECRET = os.getenv('API_SECRET_BINANCE')
_API_KEY_POLYGON = os.getenv('API_KEY_POLYGON')

_binance_client = None
_polygon_client = None

_EVENT_KEY_QUERY_STRING_PARAMETER = 'queryStringParameters'
_PARAM_KEY_FROM = 'from'
_PARAM_KEY_MARKET = 'market'
_PARAM_KEY_SYMBOL = 'symbol'

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


def get_binance_client():
    global _binance_client
    if _binance_client is None:
        _binance_client = BinanceClient(_API_KEY, _API_SECRET)
    return _binance_client

def get_polygon_client():
    global _polygon_client
    if _polygon_client is None:
        _polygon_client = PolygonClient(_API_KEY_POLYGON)
    return _polygon_client


def _get_equity_minutely_ohlcv(symbol, from_epoch_seconds):
    def epoch_seconds_to_et_str(timestamp_seconds):
        t = datetime.datetime.utcfromtimestamp(timestamp_seconds)
        t_utc = pytz.utc.localize(t)
        t_tz = t_utc.astimezone(_TIMEZONE_US_EAST)
        return t_tz.strftime('%Y-%m-%d')

    date_str = epoch_seconds_to_et_str(from_epoch_seconds)
    print('_get_equity_minutely_ohlcv', 'date_str', date_str)
    candles_polygon = get_polygon_client().stocks_equities_aggregates(symbol, 1, "minute", date_str, date_str, unadjusted=False)
    r = [{'o': p['o'], 'h': p['h'], 'l': p['l'], 'c': p['c'], 'v': p['v'], 't': p['t'] // 1000} for p in candles_polygon.results]
    return r

def _get_binance_minutely_ohlcv(symbol, from_epoch_seconds):
    candles_binance = get_binance_client().get_historical_klines(symbol, BinanceClient.KLINE_INTERVAL_1MINUTE, from_epoch_seconds * 1000)
    r = [{'o': float(p[1]), 'h': float(p[2]), 'l': float(p[3]), 'c': float(p[4]), 'v': float(p[5]), 't': p[0] // 1000} for p in candles_binance]
    return r


def lambda_handler(event, context):
    query_string_parameters = event[_EVENT_KEY_QUERY_STRING_PARAMETER]
    print("query_string_parameters:", query_string_parameters)

    if not query_string_parameters:
        res = _RESPONSE_400
        res['body'] = json.dumps('query_string_parameters is empty.')
        return res
    
    if _PARAM_KEY_MARKET not in query_string_parameters:
        res = _RESPONSE_400
        res['body'] = json.dumps('{k} is not found.'.format(k=_PARAM_KEY_MARKET))
        return res

    if _PARAM_KEY_SYMBOL not in query_string_parameters:
        res = _RESPONSE_400
        res['body'] = json.dumps('{k} is not found.'.format(k=_PARAM_KEY_SYMBOL))
        return res

    if _PARAM_KEY_FROM not in query_string_parameters:
        res = _RESPONSE_400
        res['body'] = json.dumps('{k} is not found.'.format(k=_PARAM_KEY_FROM))
        return res
    
    market = query_string_parameters[_PARAM_KEY_MARKET]
    symbol = query_string_parameters[_PARAM_KEY_SYMBOL]
    from_t = datetime.datetime.strptime(query_string_parameters[_PARAM_KEY_FROM], _DATETIME_FORMAT)
    from_epoch_seconds = int(from_t.timestamp())
    print("from_epoch_seconds", from_epoch_seconds, "from_t:", from_t)

    items = []
    if market == 'stock':
        items = _get_equity_minutely_ohlcv(symbol, from_epoch_seconds)
    elif market == 'binance':
        items = _get_binance_minutely_ohlcv(symbol, from_epoch_seconds)

    result = items
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': json.dumps(result, cls=DecimalEncoder)
    }





