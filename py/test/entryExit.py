
from const import *
from logger import logger
from backTest import BackTest
from tool import Tool
class EntryExit:
    
    def __init__(self,tool:Tool, backTest:BackTest, price) -> None:
        self.tool = tool
        self.back = backTest
        self.price = price  
    # エントリーシグナルを判定して成行注文を出す関数
    def entry_signal(self, flag, data,i,last_data, logic_signal):

        signal = logic_signal(last_data,i)  # ロジックごとにシグナル関数が異なるが、ここで同様に参照する

        if signal["side"] == "BUY":
            logger.info("エントリーシグナルが発生しました")
            lot, stop, flag = self.tool.calculate_lot(flag, data, i, self.price)
            if lot > 0.01:
                logger.info("{0}円で{1}BTCの買い注文を出します".format(data["close_price"], lot))

                # ここに買い注文のコードを入れる

                logger.info("{}円にストップを入れます".format(data["close_price"] - stop))
                flag["order"]["exist"] = True
                flag["order"]["side"] = "BUY"  
                flag["order"]["price"] = data["close_price"]
                flag["order"]["lot"], flag["order"]["stop"] = lot, stop
            else:
                logger.info("注文可能枚数{}が、最低注文単位に満たなかったため注文を見送ります".format(lot))        

        return flag
    
    
    # エントリーシグナルに対して指値注文を出す関数
    def entry_signal_limit(self, flag, data,logic_signal, last_data, i, entry_limit):
        
        signal = logic_signal(last_data, i)
        
        if signal["side"] == "BUY":
            logger.info("エントリーシグナルが発生しました")
            lot, stop, flag = self.tool.calculate_lot(flag, data, i, self.price)
            
            ATR = self.tool.calculate_volatility(self.price)  # self.toolに修正
            delta = round(ATR[i-1] * entry_limit)  # 指値距離はATRで管理
            
            if lot > 0.01:
                limit_1 = last_data[-1]["close_price"] - delta  # 指値価格
                logger.info("{0}円で{1}BTCの買い指値を出します".format(limit_1, lot))
                if data["low_price"] < limit_1:  # 指値の約定条件（ ＝ 現在の安値が一足前の指値を下回る ＝ 指値が刺さっている）
                    logger.info("１足前の指値({}円)が現在の安値({}円)を上回るので、指値は{}円で約定したものとみなす".format(limit_1, data["low_price"], limit_1))
                
                    # 指値注文のコードを入れる

                    logger.info("{}円にストップを入れます".format(limit_1 - stop))
                    flag["order"]["exist"] = True
                    flag["order"]["side"] = "BUY"  
                    flag["order"]["price"] = limit_1
                    flag["order"]["lot"], flag["order"]["stop"] = lot, stop
                else:
                    logger.info("指値価格({}円)が安値({}円)を下回るので、指値は約定しなかったものとみなす".format(limit_1, data["low_price"]))
            else:
                logger.info("注文可能枚数{}が、最低注文単位に満たなかったため注文を見送ります".format(lot))        

        return flag
    
    
    # サーバーに出した注文が約定したか確認する関数
    def check_order(self, flag):
        
        # 注文が約定した際に、ポジションにフラグ変数を切り替える

        flag["order"]["exist"] = False
        flag["order"]["count"] = 0
        flag["position"]["exist"] = True
        flag["position"]["side"] = flag["order"]["side"]
        flag["position"]["price"] = flag["order"]["price"]
        flag["position"]["stop"] = flag["order"]["stop"]
        flag["position"]["lot"] = flag["order"]["lot"]

        return flag
    
    
    # 手仕舞いのシグナルが出たら決済の成行注文
    def close_position(self, flag, data,last_data, i , logic_signal):

        if flag["position"]["exist"] == False:
            return flag

        flag["position"]["count"] += 1
        
        signal = logic_signal(last_data, i)
        
        if flag["position"]["side"] == "BUY":
            if signal["side"] == "SELL":
                logger.info("エグジットのシグナルが発生しました")
                logger.info(str(data["close_price"]) + "円でポジションを決済します")                                          

                # 決済の注文コードを入れる

                self.back.records(flag, data, data["close_price"])
                flag["position"]["exist"] = False
                flag["position"]["count"] = 0

        return flag
    
    
    # エグジットシグナルに対して指値注文で決済する関数
    def close_position_limit(self, flag, data, logic_signal, last_data, i, exit_limit):

        if flag["position"]["exist"] == False:
            return flag

        flag["position"]["count"] += 1
        
        signal = logic_signal(last_data,i)
        
        ATR = self.tool.calculate_volatility(self.price)
        delta = round(ATR[i-1] * exit_limit)

        if flag["position"]["side"] == "BUY":
            if signal["side"] == "SELL":
                logger.info("エグジットのシグナルが発生しました")
                limit_2 = last_data[-1]["close_price"] + delta
                logger.info("{0}円で売り指値を出します".format(limit_2))
                if data["high_price"] > limit_2:
                    logger.info("１足前の指値({}円)が高値({}円)を下回ったので指値が約定したとみなし、ポジションを決済します".format(limit_2, data["high_price"]))                                          

                    # 決済の指値注文コードを入れる

                    self.back.records(flag, data, limit_2)  # 取引の結果を記録するrecords関数の引数にlimitを指定する
                    flag["position"]["exist"] = False
                    flag["position"]["count"] = 0
                else:
                    logger.info("指値価格({}円)が高値({}円)を上回ったので、指値は約定しなかったとみなす".format(limit_2, data["high_price"]))

        return flag


    # 損切りラインにかかったら成行注文で決済する関数
    def stop_position(self, flag, data, i, chart_sec):

        if flag["position"]["side"] == "BUY":
            stop_price = flag["position"]["price"] - flag["position"]["stop"]
            if data["low_price"] < stop_price:
                logger.info("{0}円の損切りラインに引っ掛かりました".format(stop_price))
                ATR = self.tool.calculate_volatility()
                stop_price = round(stop_price - 2 * ATR[i-1] / (chart_sec / 60))
                logger.info(str(stop_price) + "円あたりで成行注文を出してポジションを決済します。\n")

                # 決済の注文コードを入れる

                self.back.records(flag, data, stop_price, "STOP")
                flag["position"]["exist"] = False
                flag["position"]["count"] = 0

        return flag