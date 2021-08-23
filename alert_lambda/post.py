import boto3
import datetime, uuid, re

from boto3.dynamodb.conditions import Key, Attr
_RESOURCE_DYNAMODB = 'dynamodb'
_TABLE_NAME = 'alerts'
_DATABASE_KEY_USER = 'user'

_DYNAMO_DB = boto3.resource(_RESOURCE_DYNAMODB)
_TABLE = _DYNAMO_DB.Table(_TABLE_NAME)

_ALLOWED_WINDOWS = set(['10', '20', '60', '360'])
_ALLOWED_THRESHOLD = set(['5', '10', '20', '30'])
_ALLOWED_MOVE_TYPE = set(['jump', 'drop'])
_ALLOWED_NOTIFICATION_DESTINATION_TYPE = set(['email', 'sms'])

_EMAIL_REGEX = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'


class PostAlertParameter:
    def __init__(
        self, 
        user_id, 
        alert_name, 
        description, 
        symbols, 
        time_window_minutes, 
        threshold_percent, 
        move_type, 
        notification_destination_type, 
        notification_destination, 
        alert_id = None):
        self.user_id = user_id
        self.alert_name = alert_name
        self.description = description
        self.symbols = symbols
        self.time_window_minutes = time_window_minutes
        self.threshold_percent = threshold_percent
        self.move_type = move_type
        self.notification_destination_type = notification_destination_type
        self.notification_destination = notification_destination
        self.alert_id = alert_id

    def _validate_email(self, email):
        if not email:
            return True
        return re.fullmatch(_EMAIL_REGEX, email)

    def validate(self):
        if not self.alert_name:
            return False, "Alert name can not be empty."
        if not self.symbols:
            return False, "Symbol can not be empty."
        if not self.time_window_minutes or self.time_window_minutes not in _ALLOWED_WINDOWS:
            return False, "Window {w} is not allowed.".format(w=self.time_window_minutes)
        if not self.threshold_percent or self.threshold_percent not in _ALLOWED_THRESHOLD:
            return False, "Threshold {th} is not allowed.".format(th=self.threshold_percent)
        if not self.move_type or self.move_type not in _ALLOWED_MOVE_TYPE:
            return False, "Move type {m} is not allowed.".format(th=self.move_type)
        if not self.notification_destination_type or self.notification_destination_type not in _ALLOWED_NOTIFICATION_DESTINATION_TYPE:
            return False, "Destination type {d} is not allowed.".format(d=self.notification_destination_type)
        if self.notification_destination_type == 'email' and not self._validate_email(self.notification_destination):
            return False, ""
        return True, None


def post_alert(parameter):
    modified_epoch_seconds = int(datetime.datetime.utcnow().strftime('%s'))
    alert_id = parameter.alert_id
    if alert_id is None:
        alert_id = str(uuid.uuid1())
    item = {
           'modified_epoch_seconds': str(modified_epoch_seconds),
           'user_id': parameter.user_id,
           'alert_name': parameter.alert_name,
           'description': parameter.description,
           'symbol': parameter.symbols,
           'window_size_minutes': str(parameter.time_window_minutes),
           'threshold_percent': str(parameter.threshold_percent),
           'move_type': parameter.move_type,
           'notification_destination_type': parameter.notification_destination_type,
           'notification_destination': parameter.notification_destination,
           'alert_id': alert_id
        }
    print(item)
    try:
        _TABLE.put_item(
            Item=item
        )
    except Exception as ex:
        print(ex)
    return alert_id