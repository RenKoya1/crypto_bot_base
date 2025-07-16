
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd

from logger import logger
from const import *


class BackTest:
    
    def records(self, flag, data, close_price, close_type=None):

        # 取引手数料等の計算
        entry_price = int(round(flag["position"]["price"] * flag["position"]["lot"]))
        exit_price = int(round(close_price * flag["position"]["lot"]))
        trade_cost = round(exit_price * slippage)

        logger.info("スリッページ・手数料として " + str(trade_cost) + "円を考慮します")
        flag["records"]["slippage"].append(trade_cost)

        # 手仕舞った日時と保有期間を記録
        flag["records"]["date"].append(data["close_time_dt"])
        flag["records"]["holding-periods"].append(flag["position"]["count"])

        # 損切りにかかった回数をカウント
        if close_type == "STOP":
            flag["records"]["stop-count"].append(1)
        else:
            flag["records"]["stop-count"].append(0)

        # 値幅の計算
        buy_profit = exit_price - entry_price - trade_cost
        sell_profit = entry_price - exit_price - trade_cost

        # 利益が出てるかの計算
        if flag["position"]["side"] == "BUY":
            flag["records"]["side"].append("BUY")
            flag["records"]["profit"].append(buy_profit)
            flag["records"]["return"].append(round(buy_profit / entry_price * 100, 4))
            flag["records"]["funds"] = flag["records"]["funds"] + buy_profit
            if buy_profit > 0:
                logger.info(str(buy_profit) + "円の利益です")
            else:
                logger.info(str(buy_profit) + "円の損失です")
                
        return flag
    
    
    # バックテストの集計用の関数
    def backtest(self, flag, price, last_data):
        
        # 本文からの移植
        print("--------------------------")
        print("テスト期間：")
        print("開始時点 ： " + str(price[0]["close_time_dt"]))
        print("終了時点 ： " + str(price[-1]["close_time_dt"]))
        print(str(len(price)) + "件のローソク足データで検証")
        print("--------------------------")
        

        # 成績を記録したPandas DataFrameを作成
        records = pd.DataFrame({
            "Date"     : pd.to_datetime(flag["records"]["date"]),
            "Profit"   : flag["records"]["profit"],
            "Side"     : flag["records"]["side"],
            "Rate"     : flag["records"]["return"],
            "Stop"     : flag["records"]["stop-count"],
            "Periods"  : flag["records"]["holding-periods"],
            "Slippage" : flag["records"]["slippage"]
        })

        # 連敗回数をカウントする
        consecutive_defeats = []
        defeats = 0
        for p in flag["records"]["profit"]:
            if p < 0:
                defeats += 1
            else:
                consecutive_defeats.append(defeats)
                defeats = 0

        # テスト日数を集計
        time_period = datetime.fromtimestamp(last_data[-1]["close_time"]) - datetime.fromtimestamp(last_data[0]["close_time"])
        time_period = int(time_period.days)

        # 総損益の列を追加する
        records["Gross"] = records.Profit.cumsum()

        # 資産推移の列を追加する
        records["Funds"] = records.Gross + start_funds

        # 最大ドローダウンの列を追加する
        records["Drawdown"] = records.Funds.cummax().subtract(records.Funds)
        records["DrawdownRate"] = round(records.Drawdown / records.Funds.cummax() * 100, 1)

        # 買いエントリーと売りエントリーだけをそれぞれ抽出する
        buy_records = records[records.Side.isin(["BUY"])]
        # sell_records = records[records.Side.isin(["SELL"])]

        # 月別のデータを集計する
        records["月別集計"] = pd.to_datetime(records.Date.apply(lambda x: x.strftime('%Y/%m')))
        grouped = records.groupby("月別集計")

        month_records = pd.DataFrame({
            "Number"   : grouped.Profit.count(),
            "Gross"    : grouped.Profit.sum(),
            "Funds"    : grouped.Funds.last(),
            "Rate"     : round(grouped.Rate.mean(), 2),
            "Drawdown" : grouped.Drawdown.max(),
            "Periods"  : grouped.Periods.mean()
        })

        print("バックテストの結果")
        print("--------------------------")
        print("買いエントリーの成績")
        print("--------------------------")
        print("トレード回数   :  {}回".format(len(buy_records)))
        print("勝率         :  {}％".format(round(len(buy_records[buy_records.Profit > 0]) / len(buy_records) * 100, 1)))
        print("平均リターン   :  {}％".format(round(buy_records.Rate.mean(), 2)))
        print("総損益        :  {}円".format(buy_records.Profit.sum()))
        print("平均保有期間   :  {}足分".format(round(buy_records.Periods.mean(), 1)))
        print("損切りの回数   :  {}回".format(buy_records.Stop.sum()))

        print("--------------------------")
        print("総合パフォーマンス")
        print("--------------------------")
        print("全トレード数      :  {}回".format(len(records)))
        print("勝率            :  {}％".format(round(len(records[records.Profit > 0]) / len(records) * 100, 1)))
        print("平均リターン      :  {}％".format(round(records.Rate.mean(), 2)))
        print("平均保有期間      :  {}足分".format(round(records.Periods.mean(), 1)))
        print("損切りの回数      :  {}回".format(records.Stop.sum()))
        print("")
        print("最大の勝ちトレード :  {}円".format(records.Profit.max()))
        print("最大の負けトレード :  {}円".format(records.Profit.min()))
        print("最大ドローダウン   :  {0}円／{1}％".format(-1 * records.Drawdown.max(), -1 * records.DrawdownRate.loc[records.Drawdown.idxmax()]))
        print("最大連敗回数      :  {}回".format(max(consecutive_defeats)))
        print("利益合計         :  {}円".format(records[records.Profit > 0].Profit.sum()))
        print("損失合計         :  {}円".format(records[records.Profit < 0].Profit.sum()))
        print("最終損益         :  {}円".format(records.Profit.sum()))
        print("")
        print("初期資金         :  {}円".format(start_funds))
        print("最終資金         :  {}円".format(records.Funds.iloc[-1]))
        print("運用成績         :  {}％".format(round(records.Funds.iloc[-1] / start_funds * 100, 2)))
        print("手数料合計       :  {}円".format(-1 * records.Slippage.sum()))

        print("-----------------------------------")
        print("各成績指標")
        print("-----------------------------------")
        print("CAGR(年間成長率)     :  {}％".format(round((records.Funds.iloc[-1] / start_funds) ** (time_period / 365) * 100 - 100, 2)))
        print("MARレシオ           :  {}".format(round((records.Funds.iloc[-1] / start_funds - 1) * 100 / records.DrawdownRate.max(), 2)))
        print("シャープレシオ        :  {}".format(round(records.Rate.mean() / records.Rate.std(), 2)))
        print("プロフィットファクター :  {}".format(round(records[records.Profit>0].Profit.sum() / abs(records[records.Profit<0].Profit.sum()), 2)))
        print("損益レシオ           :  {}".format(round(records[records.Profit>0].Rate.mean() / abs(records[records.Profit<0].Rate.mean()), 2)))

        print("-----------------------------------")
        print("月別の成績")

        for index,row in month_records.iterrows():
            print("-----------------------------------")
            print("{0}年{1}月の成績".format(index.year, index.month))
            print("-----------------------------------")
            print("トレード数      :  {}回".format(row.Number.astype(int)))
            print("月間損益        :  {}円".format(row.Gross.astype(int)))
            print("平均リターン     :  {}％".format(row.Rate))
            print("継続ドローダウン :  {}円".format(-1 * row.Drawdown.astype(int)))
            print("月末資金        :  {}円".format(row.Funds.astype(int)))

        # 損益曲線をプロット
        plt.plot(records.Date, records.Funds)
        plt.xlabel("Date")
        plt.ylabel("Balance")
        plt.xticks(rotation=50) # x軸の目盛りを50度回転

        plt.show()
        
        
    # フラグ変数管理の関数
    def flags(self):
        
        flag = {
            "order" : {
                "exist" : False,
                "side" : "",
                "price" : 0,
                "stop" : 0,
                "ATR" : 0,
                "lot" : 0,
                "count" : 0
            },
            "position" : {
                "exist" : False,
                "side" : "",
                "price" : 0,
                "stop" : 0,
                "ATR" :0,
                "lot" : 0,
                "count" : 0
            },
            "records" : {
                "date" : [],
                "profit" : [],
                "return" : [],
                "side" : [],
                "stop-count" : [],
                "funds" : start_funds,
                "holding-periods" : [],
                "slippage" : [],
                "log" : []
            }
        }
        
        return flag