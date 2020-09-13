import backtrader as bt
import datetime

import pandas as pd
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])
import argparse
from mylogs import mylog

class MacdStrategy(bt.Strategy):
    params = (
        ('fastperiod', 10),
        ('slowperiod', 24),
        ('signalperiod', 8),
    )
    
        
    def __init__(self):
        
        kwargs = {
            'fastperiod': self.p.fastperiod,
            'fastmatype': bt.talib.MA_Type.EMA,
            'slowperiod': self.p.slowperiod,
            'slowmatype': bt.talib.MA_Type.EMA,
            'signalperiod': self.p.signalperiod,
            'signalmatype': bt.talib.MA_Type.EMA,
        }

        # Add a Macd indicator
        self.macd = bt.talib.MACDEXT(
             self.data0.close, **kwargs)
        self.crossover = bt.indicators.CrossOver(self.macd.macd, self.macd.macdsignal, plot=False)
        self.above = bt.And(self.macd.macd>0.0, self.macd.macdsignal>0.0)

        #self.buy_signal = bt.And(self.above, self.crossover==1)
        self.buy_signal = self.crossover==1
        self.sell_signal = (self.crossover==-1)
        # To keep track of pending orders
        self.order = None
        
    # def prenext(self):
    #     print("prenext")
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            # Write down: no pending order
            self.order = None

    def next(self):
        # print('data len= ' + str(len(self.data0)))
        # Check if an order is pending ... if yes, we cannot send a 2nd one
        other = self.macd.macd[0] - self.macd.macd[-1]
        before = self.macd.macd[-1] -self.macd.macd[-2]
        macdbuy = (other>0 and before<0)
        macdsell = (other<0 and before>0)
        if self.order:
            return
        
        # Check if we are in the market
        if not self.position:
            # Not yet ... we MIGHT BUY if ...
            if self.buy_signal[0] or macdbuy:
                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy()
        else:
            # Already in the market ... we might sell
            if self.sell_signal[0] or macdsell:
                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()

def parse_args(pargs=None):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(' - '.join([
            'BTFD',
            'http://dark-bid.com/BTFD-only-strategy-that-matters.html',
            ('https://www.reddit.com/r/algotrading/comments/5jez2b/'
             'can_anyone_replicate_this_strategy/')]))
        )
    parser.add_argument('--all', required=False, action='store_true',
                        help='run all a stock')

    parser.add_argument('--s', required=False, default='000001',
                        help='to test which stocks')
    return parser.parse_args(pargs)

def runstrat(args=None):
    args = parse_args(args)

    logger = mylog.MyLog(__name__,__file__)
    logger.instance()
    start_time = str(datetime.datetime.now())
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, 'testdata/stocklist.csv')
    stocklist = pd.read_csv(datapath,index_col=0,parse_dates=True)
    if args.all:
        profitValue = 0
        lossValue = 0
        for ts_code in stocklist['ts_code']:
            print(ts_code[0:6])
            mydatapath = os.path.join(modpath, 'testdata/day/'+ts_code[0:6]+'.csv')
            if not os.path.exists(mydatapath) :
                print(mydatapath + ' not exists,continue!!!')
                continue

            dataframe = pd.read_csv(mydatapath,index_col=0,parse_dates=True)
            if dataframe.empty:
                continue
            dataframe['openinterest'] = 0
            data = bt.feeds.PandasData(dataname=dataframe)
            cerebro = bt.Cerebro()
            cerebro.adddata(data,name = ts_code)
            cerebro.addstrategy(MacdStrategy)
            cerebro.broker.setcash(100000.0)
            cerebro.broker.setcommission(0.0005)
            cerebro.broker.set_coc(True)
            cerebro.addsizer(bt.sizers.AllInSizerInt, percents=99)
            # cerebro.addanalyzer(bt.analyzers.SQN)
            begincash = cerebro.broker.getvalue()
            print('Starting Portfolio Value: {:.2f}'.format(cerebro.broker.getvalue()))
            cerebro.run()
            # cerebro.plot()
            print('Ending Portfolio Value: {:.2f}'.format(cerebro.broker.getvalue()))
            endcash = cerebro.broker.getvalue()
            if(begincash > endcash):
                lossValue = lossValue +1
                logger.logerr(ts_code[0:6] + 'loss!')
            else:
                profitValue = profitValue +1
                logger.logerr(ts_code[0:6] + 'profit!')
        logger.logerr('profit:' + str(profitValue) + ' loss:' + str(lossValue))
    else:
        if not args.s is None:
            datapath = os.path.join(modpath, 'testdata/day/',args.s+'.csv')
        else:
            datapath = os.path.join(modpath,'testdata/bt_csv_from_toshare.csv')
        print(datapath)
        if not os.path.exists(datapath):
            print(datapath + ' not exists,pls use the correct path!!!')
            sys.exit(0)
        dataframe = pd.read_csv(datapath,index_col=0,parse_dates=True)
        dataframe['openinterest'] = 0
        data = bt.feeds.PandasData(dataname=dataframe)
        cerebro = bt.Cerebro()
        cerebro.adddata(data)
        cerebro.addstrategy(MacdStrategy)
        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(0.0005)
        cerebro.broker.set_coc(True)
        cerebro.addsizer(bt.sizers.AllInSizerInt, percents=99)
        cerebro.addanalyzer(bt.analyzers.SQN)
            
        print('Starting Portfolio Value: {:.2f}'.format(cerebro.broker.getvalue()))
        cerebro.run()
        cerebro.plot()
        print('Ending Portfolio Value: {:.2f}'.format(cerebro.broker.getvalue()))
    print('start_time = ' + start_time + ' end time =' + str(datetime.datetime.now()))


if __name__ == '__main__':
    runstrat()
