import time
import pandas as pd
from pybit.unified_trading import HTTP
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("BYBIT_API_KEY")  
API_SECRET = os.getenv("BYBIT_API_SECRET")  

session = HTTP(
    testnet=False, 
    api_key=API_KEY,
    api_secret=API_SECRET
)

symbol = "XRPUSDT"
timeframe = "60"
qty = 0.001 



def get_ohlcv(symbol, interval, limit=100):
    data = session.get_kline(
        category="linear",
        symbol=symbol,
        interval=interval,
        limit=limit
    )
    print(f"API response: {data}")  # デバッグ用
    df = pd.DataFrame(data["result"]["list"], columns=[
        "timestamp", "open", "high", "low", "close", "volume", "turnover"])
    df["close"] = df["close"].astype(float)
    return df


def trend_follow_strategy(df):
    # データ数が3未満なら何もしない
    if df["close"].iloc[-1] > df["close"].iloc[-2] > df["close"].iloc[-3]:
        return "buy"
    elif df["close"].iloc[-1] < df["close"].iloc[-2] < df["close"].iloc[-3]:
        return "sell"
    else:
        return "hold"


def get_balance():
    resp = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
    print(f"Current USDT balance: {resp}")
    # USDT残高を抽出
    try:
        balance = float(resp["result"]["list"][0]["coin"][0]["availableToWithdraw"])
    except Exception:
        balance = 0.0
    return balance


def place_order(side):
    qty = get_balance() / 60000  # 例: USDT残高を価格で割って注文数量算出（調整可）
    if qty <= 0:
        print("Insufficient balance.")
        return
    # 現在価格を取得
    df = get_ohlcv(symbol, timeframe, limit=1)
    price = float(df["close"].iloc[-1]) if len(df) > 0 else None
    if price is None:
        print("価格取得失敗")
        return
    if side == "buy":
        session.place_order(
            category="linear",
            symbol=symbol,
            side="Buy",
            orderType="Limit",
            price=price,
            qty=qty,
            timeInForce="GTC",
            reduceOnly=False
        )
        print(f"Buy limit order sent. price={price}, qty={qty}")
    elif side == "sell":
        session.place_order(
            category="linear",
            symbol=symbol,
            side="Sell",
            orderType="Limit",
            price=price,
            qty=qty,
            timeInForce="GTC",
            reduceOnly=False
        )
        print(f"Sell limit order sent. price={price}, qty={qty}")
    else:
        print("No order.")


def main():
    while True:
        df = get_ohlcv(symbol, timeframe)
        print(f"Latest data: {df.tail(1)}")
        get_balance()  # 保有量表示
        signal = trend_follow_strategy(df)
        print(f"Signal: {signal}")
        # place_order(signal)
        time.sleep(60)  

if __name__ == "__main__":
    main()
