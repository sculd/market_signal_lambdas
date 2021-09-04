import os, pytz, datetime

_TIMEZONE_US_EAST = pytz.timezone('US/EASTERN')

def get_report_lines(
    symbol, 
    current_price, timestamp_epoch_seconds,
    min_drop_percent, price_at_min_drop, min_drop_epoch_seconds, 
    max_jump_percent, price_at_max_jump, max_jump_epoch_seconds,
    window_minutes, threshold_percent, move_type):
    lines = []
    lines.append('A market sudden move was detected:')
    lines.append('{symbol} price experienced {move_type}'.format(symbol=symbol, move_type=move_type))

    threshold_percent_v = float(threshold_percent)

    def get_time_str_from_epoch(epoch):        
        def suffix(d):
            return 'th' if 11<=d<=13 else {1:'st',2:'nd',3:'rd'}.get(d%10, 'th')

        def custom_strftime(format, t):
            return t.strftime(format).replace('{S}', str(t.day) + suffix(t.day))

        t = pytz.utc.localize(datetime.datetime.utcfromtimestamp(epoch)).astimezone(_TIMEZONE_US_EAST)
        return custom_strftime('%h {S} %I:%M %p ET', t)


    drop_str = 'At {time_drop} dropped by {min_drop_percent}% to ${price_at_min_drop}'.format(
        time_drop=get_time_str_from_epoch(min_drop_epoch_seconds), min_drop_percent=round(float(min_drop_percent)), price_at_min_drop=price_at_min_drop
        ) if abs(float(min_drop_percent)) >= threshold_percent_v else ''

    jump_str = 'At {time_jump} jumped by {max_jump_percent}% to ${price_at_max_jump}'.format(
        time_jump=get_time_str_from_epoch(max_jump_epoch_seconds), max_jump_percent=round(float(max_jump_percent)), price_at_max_jump=price_at_max_jump
        ) if abs(float(max_jump_percent)) >= threshold_percent_v else ''

    former = drop_str
    latter = jump_str

    if max_jump_epoch_seconds < min_drop_epoch_seconds:
        former = jump_str
        latter = drop_str

    if former: lines.append(former)
    if latter: lines.append(latter)

    return lines
