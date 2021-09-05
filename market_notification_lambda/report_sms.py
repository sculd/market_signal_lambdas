# Download the helper library from https://www.twilio.com/docs/python/install
import os
import report
from twilio.rest import Client

account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
client = Client(account_sid, auth_token)
_FROM_NUMBER = os.getenv('TWILIO_SENDER_NUMBER')


def get_report_str(
    symbol, 
    current_price, timestamp_epoch_seconds,
    min_drop_percent, price_at_min_drop, min_drop_epoch_seconds, 
    max_jump_percent, price_at_max_jump, max_jump_epoch_seconds,
    window_minutes, threshold_percent, move_type):
    lines = report.get_report_lines(
        symbol, 
        current_price, timestamp_epoch_seconds,
        min_drop_percent, price_at_min_drop, min_drop_epoch_seconds, 
        max_jump_percent, price_at_max_jump, max_jump_epoch_seconds,
        window_minutes, threshold_percent, move_type
        )

    if not lines:
        print('empty report')
        return '<h4>empty report</h4>'

    html_str = '\n'.join(lines)

    return html_str


def send_sms_report(
    phone_number,
    symbol, 
    current_price, timestamp_epoch_seconds,
    min_drop_percent, price_at_min_drop, min_drop_epoch_seconds, 
    max_jump_percent, price_at_max_jump, max_jump_epoch_seconds,
    window_minutes, threshold_percent, move_type
    ):
     print('send_sms_report for {s}'.format(s=symbol))
     sms_str = get_report_str(
        symbol, 
        current_price, timestamp_epoch_seconds,
        min_drop_percent, price_at_min_drop, min_drop_epoch_seconds, 
        max_jump_percent, price_at_max_jump, max_jump_epoch_seconds,
        window_minutes, threshold_percent, move_type)

     message = client.messages \
                     .create(
                          body=sms_str,
                          from_=_FROM_NUMBER,
                          to=phone_number
                      )

     print(message.sid)
