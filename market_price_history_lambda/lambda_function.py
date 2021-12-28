import datetime, decimal, json, requests
import os
import pytz
from binance.client import Client as BinanceClient
from polygon import RESTClient as PolygonClient


_TIMEZONE_US_EAST = pytz.timezone('US/EASTERN')
_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
_API_KEY = os.getenv('API_KEY_BINANCE')
_API_SECRET = os.getenv('API_SECRET_BINANCE')
_API_KEY_POLYGON = os.getenv('API_KEY_POLYGON')
_OKCOIN_BASE_URL = 'https://www.okcoin.com/api'
_KRAKEN_BASE_URL = 'https://api.kraken.com/0/public'

_DATETIME_FORMAT_QUERY = '%Y-%m-%dT%H:%M:%S.000Z'
_DATETIME_FORMAT_CANDLE_HISTORY = '%Y-%m-%dT%H:%M:%S.000%z'

_binance_client = None
_polygon_client = None

_EVENT_KEY_PATH_PARAMETER = 'pathParameters'
_PATH_PARAMETER_MARKET = 'market'
_PATH_PARAMETER_SYMBOL = 'symbol'

_EVENT_KEY_QUERY_STRING_PARAMETER = 'queryStringParameters'
_PARAM_KEY_FROM = 'from'

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
    def epoch_seconds_to_et(timestamp_seconds):
        t = datetime.datetime.utcfromtimestamp(timestamp_seconds)
        t_utc = pytz.utc.localize(t)
        t_tz = t_utc.astimezone(_TIMEZONE_US_EAST)
        return t_tz

    def epoch_seconds_to_et_str(timestamp_seconds):
        t_tz = epoch_seconds_to_et(timestamp_seconds)
        return t_tz.strftime('%Y-%m-%d')

    date_str = epoch_seconds_to_et_str(from_epoch_seconds)
    print('_get_equity_minutely_ohlcv', 'date_str', date_str)
    candles_polygon = get_polygon_client().stocks_equities_aggregates(symbol, 1, "minute", date_str, date_str, unadjusted=False)
    r = [{'o': p['o'], 'h': p['h'], 'l': p['l'], 'c': p['c'], 'v': p['v'], 't': p['t'] // 1000} for p in candles_polygon.results]
    r = [p for p in r if p['t'] >= from_epoch_seconds]
    r = [p for p in r if epoch_seconds_to_et(p['t']).hour < 16] # market close at 4pm et.
    return r

def _get_binance_minutely_ohlcv(symbol, from_epoch_seconds):
    candles_binance = get_binance_client().get_historical_klines(symbol, BinanceClient.KLINE_INTERVAL_1MINUTE, from_epoch_seconds * 1000)
    r = [{'o': float(p[1]), 'h': float(p[2]), 'l': float(p[3]), 'c': float(p[4]), 'v': float(p[5]), 't': p[0] // 1000} for p in candles_binance]
    return r

def _get_okcoin_minutely_ohlcv(symbol, from_epoch_seconds):
    start = datetime.datetime.fromtimestamp(from_epoch_seconds, tz=datetime.timezone.utc).strftime(_DATETIME_FORMAT_QUERY)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    end = now.strftime(_DATETIME_FORMAT_QUERY)

    url = _OKCOIN_BASE_URL + '/spot/v3/instruments/{pair}/candles?granularity=60&start={start}&end={end}'.format(
        pair=symbol, start=start, end=end
    )
    print(url)
    r = requests.get(url)
    if not r.ok:
        return []

    js = r.json()
    ret = []
    for blob in js[::-1]:
        t = datetime.datetime.strptime(blob[0], _DATETIME_FORMAT_CANDLE_HISTORY)
        ret.append({'t': int(t.timestamp()), 'o': float(blob[1]), 'h': float(blob[2]), 'l': float(blob[3]), 'c': float(blob[4]), 'v': float(blob[5])})
    return ret

def _get_kraken_minutely_ohlcv(symbol, from_epoch_seconds):
    url = _KRAKEN_BASE_URL + '/OHLC?pair={pair}&since={since}'.format(
        pair=symbol, since=from_epoch_seconds
    )
    print(url)
    r = requests.get(url)
    if not r.ok:
        return []

    js = r.json()
    ret = []
    if js['error']:
        return ret

    symbol_key = symbol
    for k, _ in js['result'].items():
        if k == 'last': continue
        symbol_key = k

    if symbol_key not in js['result']:
        return ret

    print(js)
    for blob in js['result'][symbol_key]:
        ret.append({'t': blob[0], 'o': float(blob[1]), 'h': float(blob[2]), 'l': float(blob[3]), 'c': float(blob[4]), 'v': float(blob[6])})
    return ret

def lambda_handler(event, context):
    path_parameters = event[_EVENT_KEY_PATH_PARAMETER]

    if _PATH_PARAMETER_MARKET not in path_parameters:
        res = _RESPONSE_400
        res['body'] = json.dumps('market is not specified.')
        return res

    if _PATH_PARAMETER_SYMBOL not in path_parameters:
        res = _RESPONSE_400
        res['body'] = json.dumps('symbol is not specified.')
        return res
    market = path_parameters[_PATH_PARAMETER_MARKET]
    symbol = path_parameters[_PATH_PARAMETER_SYMBOL]
    
    query_string_parameters = event[_EVENT_KEY_QUERY_STRING_PARAMETER]

    if _PARAM_KEY_FROM not in query_string_parameters:
        res = _RESPONSE_400
        res['body'] = json.dumps('{k} is not found.'.format(k=_PARAM_KEY_FROM))
        return res
    
    from_t = datetime.datetime.strptime(query_string_parameters[_PARAM_KEY_FROM], _DATETIME_FORMAT)
    from_epoch_seconds = int(from_t.timestamp())
    print("from_epoch_seconds", from_epoch_seconds, "from_t:", from_t)

    items = []
    if market == 'stock' or market == 'polygon':
        items = _get_equity_minutely_ohlcv(symbol, from_epoch_seconds)
    elif market == 'binance':
        items = _get_binance_minutely_ohlcv(symbol, from_epoch_seconds)
    elif market == 'okcoin':
        items = _get_okcoin_minutely_ohlcv(symbol, from_epoch_seconds)
    elif market == 'kraken':
        items = _get_kraken_minutely_ohlcv(symbol, from_epoch_seconds)

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





