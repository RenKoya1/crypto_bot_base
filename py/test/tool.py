import requests
import json
from datetime import datetime
import time
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import talib

from const import *
from dotenv import load_dotenv
import os
from pybit.unified_trading import HTTP

load_dotenv()
API_KEY = os.getenv("BYBIT_API_KEY")  
API_SECRET = os.getenv("BYBIT_API_SECRET")  

session = HTTP(
    testnet=False, 
    api_key=API_KEY,
    api_secret=API_SECRET
)
class Tool:
    
    def get_price(self, interval, before=0, after=0):
        price = []
        symbol = "BTCUSDT"
        limit = 1000 # Max 1000
        # Bybitのinterval変換（例: "1", "5", "15"など）
        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        if before != 0:
            params["endTime"] = before * 1000
        if after != 0:
            params["startTime"] = after * 1000

        data = session.get_kline(**params)
        print("Bybit価格データ取得(session):", data)

        if "result" not in data or "list" not in data["result"]:
            print(f"APIエラー: {data.get('retMsg', '不明なエラー')}")
            return None

        for i in data["result"]["list"]:
            price.append({
                "close_time": int(i[0]) // 1000,
                "close_time_dt": datetime.fromtimestamp(int(i[0]) // 1000).strftime('%Y/%m/%d %H:%M'),
                "open_price": float(i[1]),
                "high_price": float(i[2]),
                "low_price": float(i[3]),
                "close_price": float(i[4])
            })
        return sorted(price, key=lambda x: x["close_time"])
    
    # json形式のファイルから価格データを読み込む関数
    def get_price_from_file(self, path , after, before):
        file = open(path, "r", encoding='utf-8')
        min = chart_sec
        price = []
        data = json.load(file)
        if data["result"][str(min)] is not None:
            for i in data["result"][str(min)]:
                if i[1] != 0 and i[2] != 0 and i[3] != 0 and i[4] != 0:
                    price.append({"close_time" : i[0],
                                 "close_time_dt" : datetime.fromtimestamp(i[0]).strftime('%Y/%m/%d %H:%M'),
                                 "open_price" : i[1],
                                 "high_price" : i[2],
                                 "low_price" : i[3],
                                 "close_price" : i[4]})               
            return price[after * -1 : before * -1]   
        else:
            print("データが存在しません")
            return None
        
            
    # talibで使用可能なデータを準備する関数
    def data_talib(self, price):
        data_talib_open = []
        data_talib_high = []
        data_talib_low = []
        data_talib_close = []
        for i in range(len(price)):
            data_talib_open.append(price[i]["open_price"])
            data_talib_high.append(price[i]["high_price"])
            data_talib_low.append(price[i]["low_price"])
            data_talib_close.append(price[i]["close_price"])
        ta = pd.DataFrame({
            "Open"   : data_talib_open,
            "High"   : data_talib_high,
            "Low"    : data_talib_low,
            "Close"  : data_talib_close
        })
        
        return ta
    
    
    # 平均ボラティリティを計算する関数
    def calculate_volatility(self, price):
        ta = self.data_talib(price)
        # ボラティリティはATRで管理（基本単位：14）
        volatility = talib.ATR(ta["High"], ta["Low"], ta["Close"], timeperiod=14)

        for i in range(14):
            if np.isnan(volatility[i]):
                volatility[i] = volatility[14]  # NaN値の場合計算不可のため、擬似的に値を置き換える
        for k in range(1, 15):
            if np.isnan(volatility[k-1]):
                volatility[k-1] = volatility[14]  # 指値・売買ロジック用の置き換え
        
        return volatility
    
    
    # 注文ロットを計算する関数
    def calculate_lot(self, flag, data, i, price):
        
        lot = 0
        balance = flag["records"]["funds"]

        volatility = self.calculate_volatility(price)
        stop = stop_range * volatility[i]

        calc_lot = np.floor(balance * trade_risk / stop * 100) / 100
        able_lot = np.floor(balance * levarage / data["close_price"] * 100) / 100
        lot = min(able_lot, calc_lot)

        flag["records"]["log"].append("現在のアカウント残高は{}円です".format(balance))
        flag["records"]["log"].append("許容リスクから購入できる枚数は最大{}BTCまでです".format(calc_lot))
        flag["records"]["log"].append("証拠金から購入できる枚数は最大{}BTCまでです".format(able_lot))

        return lot, stop, flag