import datetime, decimal
import json
import authorize, get, remove, post

_EVENT_KEY_PATH_PARAMETER = 'pathParameters'
_EVENT_KEY_QUERY_STRING_PARAMETER = 'queryStringParameters'
_EVENT_KEY_HTTP_METHOD = 'httpMethod'
_EVENT_KEY_BODY = 'body'
_PATH_PARAMETER_USER = 'user'
_PATH_PARAMETER_ALERT = 'alert'

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

_RESPONSE_404 = {
        'statusCode': 404,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        }
    }

def lambda_handler(event, context):
    print('event:', event)
    path_parameters = event[_EVENT_KEY_PATH_PARAMETER]
    user_id = path_parameters[_PATH_PARAMETER_USER]
    authed = authorize.is_authorized(event, user_id)
    if not authed:
        print('returning 403 as not authed.')
        return _RESPONSE_403

    http_method = 'GET'
    if _EVENT_KEY_HTTP_METHOD in event:
        http_method = event[_EVENT_KEY_HTTP_METHOD]

    response_body_str = json.dumps('Hello world!')
    if http_method == 'GET':
        alerts = get.get_alert(user_id)
        alerts.sort(key=lambda alert: alert['alert_name'])
        r = {'alerts': alerts}
        response_body_str = json.dumps(r)

    elif http_method == 'DELETE':
        if _PATH_PARAMETER_ALERT not in path_parameters:
            res = _RESPONSE_400
            res['body'] = json.dumps('alert id is not specified.'.format(alert_id=alert_id))
            return res
        alert_id = path_parameters[_PATH_PARAMETER_ALERT]
        alert_found = remove.delete_alert(alert_id)
        if not alert_found:
            res = _RESPONSE_404
            res['body'] = json.dumps('alert {alert_id} is not found.'.format(alert_id=alert_id))
            return res
        response_body_str = json.dumps('alert {alert_id} is deleted.'.format(alert_id=alert_id))

    elif http_method == 'POST':
        alert_id = None
        if_create_new_alert = True
        if _PATH_PARAMETER_ALERT in path_parameters:
            alert_id = path_parameters[_PATH_PARAMETER_ALERT]
            if_create_new_alert = False

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
        body = json.loads(body)
        print('json body:', body)

        keys = ['alert_name', 'description', 'symbols', 'time_window_minutes', 'threshold_percent', 'move_type', 
                'notification_to_email', 'notification_email', 'notification_to_sms', 'notification_sms']
        for key in keys:
            if key not in body:
                res = _RESPONSE_404
                res['body'] = json.dumps('body misses {key}.'.format(key=key))
                return res

        post_parameter = post.PostAlertParameter(
            user_id = user_id,
            alert_name = body['alert_name'],
            description = body['description'],
            symbols = body['symbols'],
            is_all_symbols = body['is_all_symbols'],
            time_window_minutes = body['time_window_minutes'],
            threshold_percent = body['threshold_percent'],
            move_type = body['move_type'],
            notification_to_email = body['notification_to_email'], 
            notification_email = body['notification_email'], 
            notification_to_sms = body['notification_to_sms'], 
            notification_sms = body['notification_sms'], 
            alert_id = alert_id
            )

        post_parameter_valided, error_message = post_parameter.validate()
        if not post_parameter_valided:
            res = _RESPONSE_404
            res['body'] = json.dumps('The request body is invalid: {s}'.format(s=error_message))
            return res

        alert_id = post.post_alert(post_parameter)
        if if_create_new_alert:
            response_body_str = json.dumps('alert {alert_id} was created.'.format(alert_id=alert_id))
        else:
            response_body_str = json.dumps('alert {alert_id} was modified.'.format(alert_id=alert_id))

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': response_body_str
    }
