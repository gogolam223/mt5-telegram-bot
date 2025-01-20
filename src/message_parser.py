from datetime import datetime
from telethon import events
from typing import TypedDict, Union, Literal

class ValidMessage(TypedDict):
    valid: True
    type: Literal['normal', 'noise_order']
    ticker: Literal['XAUUSD']
    trend: Literal['Up', 'Down']
    current_price: int
    message_timestamp: datetime
    raw_msg: str

class InvalidMessage(TypedDict):
    valid: False
    msg: str
    raw_msg: str

FormattedMessage = Union[ValidMessage, InvalidMessage]

MessageParserType = Literal['XAUUSD', 'XAUUSD_COMBO']

class MessageParser:
    def parse(self, msg: events.NewMessage, type: MessageParserType) -> FormattedMessage:
        if type == 'XAUUSD':
            try:
                text = msg.raw_text.splitlines()
                timestamp = msg.message.date.timestamp()
                # fx
                if text[0].strip() not in ['🔴XAUUSD🔴', '🟢XAUUSD🟢']:
                    raise TypeError
                # price
                price_texts = text[1].strip().split(' ')
                if len(price_texts) != 2 or price_texts[0] != '現價:':
                    raise TypeError
                price = float(price_texts[1]) # might throw error if it is not a float
                # trend
                trend_text = text[3].strip()
                if trend_text not in ['Potential Uptrend Started', 'Potential Downtrend Started']:
                    raise TypeError
                trend = 'Up' if trend_text == 'Potential Uptrend Started' else 'Down' if trend_text == 'Potential Uptrend Started' else None
                if trend == None:
                    raise TypeError
                return {
                    'valid': True,
                    'type': 'normal',
                    'ticker': 'XAUUSD',
                    'trend': trend,
                    'current_price': price,
                    'message_timestamp': timestamp,
                    'raw_msg': msg.raw_text,
                }
            except:
                return {
                    'valid': False,
                    "msg": f'Bot failed to read the telegram message: \n{msg.raw_text}',
                    'raw_msg': msg.raw_text,
                }
        if type == 'XAUUSD_COMBO':
            try:
                text = msg.raw_text.splitlines()
                timestamp = msg.message.date.timestamp()
                # fx
                if text[0].strip() not in ['XAUUSD 1/3 Combo']:
                    raise TypeError
                # price
                price_texts = text[2].strip().split(' ')
                if len(price_texts) != 2 or price_texts[0] != '現價:':
                    raise TypeError
                price = float(price_texts[1]) # might throw error if it is not a float
                # trend
                trend_text = text[1].strip()
                if trend_text not in ['入場方向: Short🔴', '入場方向: Long🟢']:
                    raise TypeError
                trend = 'Up' if trend_text == '入場方向: Long🟢' else 'Down' if trend_text == '入場方向: Short🔴' else None
                if trend == None:
                    raise TypeError
                # extra checking for the combo info
                fifteen_min_check = text[6].strip().split(' ')
                hour_check = text[7].strip().split(' ')
                if fifteen_min_check[0] != '15mins:' or hour_check[0] != '1hr:':
                    raise TypeError
                
                if (trend == 'Up' and fifteen_min_check[1] == 'Uptrend' and hour_check[1] == 'Uptrend') or (trend == 'Down' and fifteen_min_check[1] == 'Downtrend' and hour_check[1] == 'Downtrend'):
                    return {
                        'valid': True,
                        'type': 'normal',
                        'ticker': 'XAUUSD',
                        'trend': trend,
                        'current_price': price,
                        'message_timestamp': timestamp,
                        'raw_msg': msg.raw_text,
                    }
                else:
                    return {
                        'valid': True,
                        'type': 'noise_order',
                        'ticker': 'XAUUSD',
                        'trend': trend,
                        'current_price': price,
                        'message_timestamp': timestamp,
                        'raw_msg': msg.raw_text,
                    }
            except:
                return {
                    'valid': False,
                    "msg": f'Bot failed to read the telegram message: \n{msg.raw_text}',
                    'raw_msg': msg.raw_text,
                }
        return {
            'valid': False,
            "msg": f'[MessageParser]Unknown Message Type',
            'raw_msg': None,
        }
