import os, sendgrid, pytz, datetime
from sendgrid.helpers.mail import *
from sendgrid.helpers.mail import Mail
import report
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

_sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))

_TIMEZONE_US_EAST = pytz.timezone('US/EASTERN')


def get_report_html(
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

    lines[0] = '<strong>{l}</strong>'.format(l=lines[0])
    html_str = '<br />'.join(lines)

    return html_str


def send_email_report(
    email_address,
    symbol, 
    current_price, timestamp_epoch_seconds,
    min_drop_percent, price_at_min_drop, min_drop_epoch_seconds, 
    max_jump_percent, price_at_max_jump, max_jump_epoch_seconds,
    window_minutes, threshold_percent, move_type
    ):
    html_str = get_report_html(
        symbol, 
        current_price, timestamp_epoch_seconds,
        min_drop_percent, price_at_min_drop, min_drop_epoch_seconds, 
        max_jump_percent, price_at_max_jump, max_jump_epoch_seconds,
        window_minutes, threshold_percent, move_type)

    message = Mail(
        from_email="notification@hedgecoast.com",
        to_emails=email_address,
        subject="Market Move Signal".format(symbol=symbol),
        html_content=html_str)
    try:
        response = _sg.send(message)
        print(response.status_code)
        print(str(response.headers))
        print(response.body)
    except Exception as e:
        print(e)
