from telethon import TelegramClient, events
from .message_parser import MessageParser
from .mt5 import MetaTrader
from datetime import datetime, timezone, timedelta
from .utils import add_noise_int, random_by_probability

class TelegramBot:
    def __init__(self, config):
        self.config = config
        self.parser = MessageParser()
        self.client = TelegramClient(
            'telegram_session',
            config['telegram']['api_id'],
            config['telegram']['api_hash'],
        )
        # create mt5 instance for each traders
        traders = [None for _ in range(len(config['traders']))]
        for idx, trader in enumerate(config['traders']):
            # self, ticker: str, login: int, password: str, server: str, path: str
            traders[idx] = MetaTrader(
                trader['ticker'],
                int(trader['mt5_login']),
                trader['mt5_password'],
                trader['mt5_server'],
                trader['mt5_path'],
                trader['timezone_adjust'],
            )
        self.traders = traders
    
    async def print_telegram_channels(self):
        await self.client.start()
        dialogs = await self.client.get_dialogs()
        for item in dialogs:
            print(f"Chat ID: {item.id}, Title: {item.title}, Entity(Peer id): {item.entity.id}")
        await self.client.disconnect()
        return

    async def start(self):
        print("\nStarting Telegram-MT5 bot...\n")
        await self.client.start()

        dialogs = await self.client.get_dialogs()
        chats = []
        for signal in self.config['signals']:
            dialog = next((item for item in dialogs if str(item.id) == signal['telegram_source_chat_id']), None)
            if (dialog == None):
                print(f"Invalid Source Chat ID for signal {signal['ticker']}")
                await self.client.disconnect()
                return
            print(f"Listening to channel [{dialog.title}] for signal [{signal['ticker']}]")
            chats.append(int(signal['telegram_source_chat_id']))
        for idx, trader_config in enumerate(self.config['traders']):
            await self.send_noti(
                int(trader_config['noti_chat_id']),
                f'MT5 bot started:\nTicker: {trader_config['ticker']}\nServer: {trader_config['mt5_server']}\nAccount: {trader_config['mt5_login']}',
                trader_config['id']
            )
            
        self.client.add_event_handler(
            self.handle_channel_message,
            events.NewMessage(chats=chats)
        )
        
        print("Bot started\n")
        await self.client.run_until_disconnected()
    
    async def send_noti(self, chat_id: int, message: str, title: str | None = None,):
        if self.client.is_connected():
            formmatted_message = (f'[{title}]\n' + message) if title != None else message
            # print(formmatted_message)
            await self.client.send_message(entity=chat_id, message=formmatted_message)
        else:
            raise SystemError("Telegram Client is not connected")
        
    async def handle_channel_message(self, event):
        message = event.message
        # print(f"New message: {message.text}")
        source_peer_id = None
        if (hasattr(message.peer_id, 'chat_id')):
            source_peer_id = message.peer_id.chat_id
        elif (hasattr(message.peer_id, 'channel_id')):
            source_peer_id = message.peer_id.channel_id
        print("source_peer_id: " + str(source_peer_id))
        if source_peer_id == None:
            raise ValueError("Cannot find Source Peer Id from message")

        signal = next(
            (item for item in self.config['signals'] if abs(int(item["telegram_source_peer_id"])) == abs(int(source_peer_id))), None
        )
        # print(f"match signal: {signal['ticker']}")
        if signal == None:
            raise ValueError("Cannot find match ticker")
        
        for idx, trader_config in enumerate(self.config['traders']):
            # only execute if this trader's ticker matches with signal's
            if trader_config['ticker'] != signal['ticker']:
                continue

            # parse telegram msg
            result = self.parser.parse(event, signal['message_type'])
            # print(result)

            if result['valid']:
                # 1. check TG price vs market price
                tick_data = self.traders[idx].get_tick_data()
                order_type = None
                if result['trend'] == 'Up':
                    order_type = 'BUY'
                    if abs(tick_data['ask'] - result['current_price']) > float(trader_config['acceptable_price_diff']):
                        await self.send_noti(
                            int(trader_config['noti_chat_id']),
                            f'Tick price [{tick_data['ask']}] & message price [{result['current_price']}] diff > {trader_config['acceptable_price_diff']}',
                            trader_config['id']
                        )
                        continue
                if result['trend'] == 'Down':
                    order_type = 'SELL'
                    if abs(tick_data['bid'] - result['current_price']) > float(trader_config['acceptable_price_diff']):
                        await self.send_noti(
                            int(trader_config['noti_chat_id']),
                            f'Tick price [{tick_data['bid']}] & message price [{result['current_price']}] diff > {trader_config['acceptable_price_diff']}',
                            trader_config['id']
                        )
                        continue
                if order_type not in ['BUY', 'SELL']:
                    # sanity check
                    await self.send_noti(
                        int(trader_config['noti_chat_id']),
                        f'Unknown order_type, check bot terminal: ' + str(order_type),
                        trader_config['id']
                    )
                    raise TypeError

                
                # 2. check open positions counts
                positions = self.traders[idx].get_positions(trader_config['ticker'])
                buy_positions = [p for p in positions if p['type'] == 0] # ENUM_POSITION_TYPE.POSITION_TYPE_BUY 
                sell_positions = [p for p in positions if p['type'] == 1] # ENUM_POSITION_TYPE.POSITION_TYPE_SELL
                if order_type == 'BUY' and len(buy_positions) >= trader_config['max_total_positions']['buy']:
                    await self.send_noti(
                        int(trader_config['noti_chat_id']),
                        f'Received telegram message but there is/are {len(buy_positions)} buy order already (Max: {trader_config['max_total_positions']['buy']})',
                        trader_config['id']
                    )
                    continue
                if order_type == 'SELL' and len(sell_positions) >= trader_config['max_total_positions']['sell']:
                    await self.send_noti(
                        int(trader_config['noti_chat_id']),
                        f'Received telegram message but there is/are {len(sell_positions)} sell order already (Max: {trader_config['max_total_positions']['sell']})',
                        trader_config['id']
                    )
                    continue

                # 3. check time - within 30s of signal receive message time vs VM time
                if abs(tick_data['timestamp'] - result['message_timestamp']) > 30:
                    await self.send_noti(
                        int(trader_config['noti_chat_id']),
                        f'Tick timestamp [{tick_data['timestamp']}] & message timestamp [{result['message_timestamp']}] diff > 30',
                        trader_config['id']
                    )
                    continue

                if result['type'] == 'normal':
                    # 4. daily margin
                    today = datetime.now(timezone(timedelta(hours=int(trader_config['daily_margin_cutoff_timezone'])))).isoformat()
                    last_cutoff_timestamp = datetime.fromisoformat(f'{today[0:10]}T00:00:00+{trader_config['daily_margin_cutoff_timezone']}:00').timestamp()
                    equity = self.traders[idx].get_current_equity()
                    prev_equity = self.traders[idx].get_previous_equity(last_cutoff_timestamp)
                    if prev_equity - equity > int(trader_config['daily_margin']):
                        await self.send_noti(
                            int(trader_config['noti_chat_id']),
                            f'Reached daily margin:\nPrevious Equity: {prev_equity}\nCurrent Equity: {equity}\nMargin: {trader_config['daily_margin']}',
                            trader_config['id']
                        )
                        continue

                    # 5. order probability, reverse the value to make the code cleaner
                    if random_by_probability(100 - trader_config['order_probability']):
                        await self.send_noti(
                            int(trader_config['noti_chat_id']),
                            f'Not handling this executing (order probability: {trader_config['order_probability']}%)',
                            trader_config['id']
                        )
                        continue

                    # 6. place order
                    orders_id = []
                    for order_config in trader_config['orders']:
                        try:
                            order_result = self.traders[idx].place_order(
                                float(order_config['lot']),
                                order_type,
                                add_noise_int(order_config['sl'], order_config['noise_sl']),
                                add_noise_int(order_config['tp'], order_config['noise_tp']),
                                int(order_config['deviation']),
                                "" # TODO: comment in mt5
                            )
                            orders_id.append(order_result.order)
                        except Exception as e:
                            await self.send_noti(
                                int(trader_config['noti_chat_id']),
                                f'Unable to place order for this config, please check bot terminal\n' + str(order_config),
                                trader_config['id']
                            )
                            raise e
                    await self.send_noti(
                        int(trader_config['noti_chat_id']),
                        f'Buy orders placed: ' + str(orders_id),
                        trader_config['id']
                    )

                elif result['type'] == 'noise_order':
                    # TODO: noise order
                    await self.send_noti(
                        int(trader_config['noti_chat_id']),
                        f'Received noise orders: ' + result['raw_msg'],
                        trader_config['id']
                    )
                    return
            else:
                await self.send_noti(
                    int(trader_config['noti_chat_id']),
                    result['msg'],
                    trader_config['id']
                )




# Example usage
if __name__ == "__main__":
    import json
    import asyncio
    with open('config.json', 'r') as file:
        config = json.load(file)
    bot = TelegramBot(config)
    # asyncio.run(bot.print_telegram_channels())
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("\nBot stopped.")