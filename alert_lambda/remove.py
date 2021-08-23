import boto3

from boto3.dynamodb.conditions import Key, Attr
_RESOURCE_DYNAMODB = 'dynamodb'
_TABLE_NAME = 'alerts'
_DATABASE_KEY_ALERT = 'alert_id'

_DB = boto3.resource(_RESOURCE_DYNAMODB)
_TABLE = _DB.Table(_TABLE_NAME)

def _is_present(alert_id):
    response = _TABLE.query(
        KeyConditionExpression=Key(_DATABASE_KEY_ALERT).eq(alert_id)
    )
    items = response['Items']
    return len(items) > 0

def delete_alert(alert_id):
    try:
        if not _is_present(alert_id):
            return False
        _TABLE.delete_item(
            Key={
                _DATABASE_KEY_ALERT: alert_id
            }
        )
    except Exception as ex:
        print(ex)
        return False

    return True
