import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logic.bbands import Bbands
from tool import Tool
from const import *
from backTest import BackTest
from entryExit import EntryExit
import time


tool = Tool()
back = BackTest()

def main():
    # 価格チャートを取得
    price = tool.get_price(chart_sec, after=0)

    enex = EntryExit(tool=tool, backTest=back, price=price)

    logic = Bbands(tool, price=price)
    # フラグ変数
    flag = back.flags()

    need_term = 1
    last_data = []
    i = 0
    i = 0

    print(price)
    # メインのループ文
    while i < len(price):

        # 指値のため、一足遅く動かすので、last_dataが少し必要
        if len(last_data) < need_term:
            last_data.append(price[i])
            i += 1
            continue
        
        data = price[i]

        if flag["order"]["exist"]:
            flag = enex.check_order(flag)

        if flag["position"]["exist"]:
            # flag = enex.stop_position(flag)
            flag = enex.close_position_limit(flag, data, logic.logic_signal, last_data, i, exit_limit=logic.exit_limit)    

        else:
            flag = enex.entry_signal_limit(flag,data, logic.logic_signal, last_data, i, entry_limit=logic.entry_limit) 

        last_data.append(data)
        i += 1
        time.sleep(wait)

    back.backtest(flag, price, last_data)


if __name__ == "__main__":
    main()
    print("FINISHED")