import boto3

from boto3.dynamodb.conditions import Key, Attr
_RESOURCE_DYNAMODB = 'dynamodb'
_TABLE_NAME = 'alerts'
_DATABASE_KEY_USER = 'user_id'


def get_alert(user_id):
    dynamodb = boto3.resource(_RESOURCE_DYNAMODB)
    table = dynamodb.Table(_TABLE_NAME)

    response = table.query(
        IndexName='user_id-index',
        KeyConditionExpression=Key(_DATABASE_KEY_USER).eq(user_id)
    )

    items = response['Items']
    return items
