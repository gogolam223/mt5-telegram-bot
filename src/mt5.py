import MetaTrader5 as mt5
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Literal
# from pprint import pprint

class MetaTrader:
    def __init__(self, ticker: str, login: int, password: str, server: str, path: str, timezone_adjust: int):
        self.login = login
        self.password = password
        self.server = server
        self.ticker = ticker
        self.path = path
        self.timezone_adjust = -1 * 60 * 60 * timezone_adjust

        if not mt5.initialize(
                path=path, # eg. "C:/Program Files/Alpari MT5/terminal64.exe"
                login=login,
                password=password,
                server=server
            ):
            raise RuntimeError("Failed to initialize MetaTrader5")

    def shutdown(self):
        mt5.shutdown()

    def is_market_avail(self) -> bool:
        # TODO: this method should check whether the market is open or close
        # but for now we just let mt5 give us error while making position
        return True
    
    def place_order(
            self,
            lot: float,
            order_type: Literal['BUY', 'SELL'],
            sl_point: float,
            tp_point: float,
            deviation = 20,
            comment = 'Opened by MT5-TELEGRAM-BOT'
        ):
        tick_data = self.get_tick_data()
        if order_type == 'BUY':
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.ticker,
                "volume": lot,
                "type": mt5.ORDER_TYPE_BUY,
                "price": tick_data['ask'],
                "sl": tick_data['ask'] - sl_point * tick_data['point'],
                "tp": tick_data['ask'] + tp_point * tick_data['point'],
                "deviation": deviation,
                "magic": 123456,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
        elif order_type == 'SELL':
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.ticker,
                "volume": lot,
                "type": mt5.ORDER_TYPE_SELL,
                "price": tick_data['bid'],
                "sl": tick_data['bid'] + sl_point * tick_data['point'],
                "tp": tick_data['bid'] - tp_point * tick_data['point'],
                "deviation": 20,
                "magic": 0,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
        else:
            raise TypeError("order_type Type Error")
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"Failed to add position: {result.comment}")
        return result

    def get_tick_data(self) -> Dict[str, Any]:
        info = mt5.symbol_info(self.ticker)
        tick = mt5.symbol_info_tick(self.ticker)
        if not tick:
            raise RuntimeError("Failed to get tick data")

        return {
            "timestamp": tick.time + self.timezone_adjust,
            "bid": tick.bid,
            "ask": tick.ask,
            "point": info.point,
        }

    def get_positions(self, ticker = None) -> List[Dict[str, Any]]:
        positions = mt5.positions_get(symbol=ticker) if ticker != None else mt5.positions_get()
        # print(positions)
        return [
            {
                "symbol": pos.symbol,
                "type": pos.type,
                "time": datetime.fromtimestamp(pos.time + self.timezone_adjust),
                "volume": pos.volume,
                "price_open": pos.price_open,
                "price_current": pos.price_current,
                "sl": pos.sl,
                "tp": pos.tp,
            } for pos in positions]
    
    def get_current_equity(self) -> float:
        account_info = mt5.account_info()
        if account_info != None:
            return account_info.equity
        else:
            print("Cannot get current equity, acc info: ", account_info)
            raise ValueError
    
    def get_previous_equity(self, timestamp) -> float:
        current = self.get_current_equity()
        # 1. closed positions (deal)
        from_date = datetime.fromtimestamp(timestamp - self.timezone_adjust)
        to_date = datetime.now() - timedelta(seconds=self.timezone_adjust)

        deals = mt5.history_deals_get(from_date, to_date)
        # pprint(deals)
        profit = 0
        for deal in deals:
            profit += deal.profit
            profit += deal.commission

        # 2. existing positions
        positions = mt5.positions_get()
        # pprint(positions)
        for position in positions:
            profit += position.profit
        # print(profit)
        # print(current - profit)
        
        return current - profit

# Example usage
if __name__ == "__main__":
    ticker = ''
    server = ''
    login = 0
    password = ''
    path = ''
    timezone_adjust = 2

    mt = MetaTrader(ticker ,login, password, server, path, timezone_adjust)
    try:
        # Getting tick data example
        tick_data = mt.get_tick_data()
        print(f"Tick data: {tick_data}")

        equity = mt.get_current_equity()
        print(f"Equity: {equity}")

        prev_equity = mt.get_previous_equity(1737338986)
        print(f"Previous Equity: {prev_equity}")

        # Getting positions example
        # positions = mt.get_positions('XAUUSD')
        # print(f"Positions: {positions}")
    finally:
        mt.shutdown()



