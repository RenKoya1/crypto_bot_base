import talib

class Bbands: 
    bbands_period = 10  # ボリンジャーバンドに用いる期間設定
    std_value = 2       # ボリンジャーバンドに用いる標準偏差の数値設定
    entry_limit = 1.0   # エントリー時の指値距離に用いるATRの係数（参考値：0.1〜1.5）
    exit_limit = 1.0  
    
    def __init__(self, tool,price):
        self.tool = tool
        self.price= price
    
    def calculate_bbands(self,value_1, value_2, tool,price):
        ta = tool.data_talib(price)
        # talibを用いたボリンジャーバンドの計算
        bbands_upper, bbands_middle, bbands_lower = talib.BBANDS(ta["Close"], timeperiod=value_1, nbdevup=value_2, nbdevdn=value_2, matype=0)
    
        return bbands_upper, bbands_middle, bbands_lower


    # ボリンジャーバンドのエントリー/エグジットシグナルを判定する関数
    def logic_signal(self, last_data, i):
        # 計算に用いる数値の準備
        bbands_upper, bbands_middle, bbands_lower = self.calculate_bbands(self.bbands_period, self.std_value, self.tool, self.price)
        
        # -1ずつずらすことに注意（指値の場合は過去の情報を使う必要があるため）
        # エントリーサイン：+２σのラインを現在の株価が上抜け
        if last_data[-1]["high_price"] > bbands_upper[i-1]:
            return {"side":"BUY", "price":last_data[-1]["close_price"]}
        
        # エグジットサイン：±０σのラインを現在の株価が下抜け
        if last_data[-1]["low_price"] < bbands_middle[i-1]:
            return {"side":"SELL", "price":last_data[-1]["close_price"]}
        
        return {"side":None, "price":0}

