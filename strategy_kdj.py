import backtrader as bt
import datetime

import pandas as pd
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])
import argparse

from mylogs import mylog

class KDJ(bt.Indicator):
    lines = ('K','D','J')

    params = (
        ('period', 9),
        ('period_dfast', 3),
        ('period_dslow', 3),
    )
    
    plotlines = dict(
        J=dict(
            _fill_gt=('K', ('red', 0.50)),
            _fill_lt=('K', ('green', 0.50)),
        )
    )
    
    def __init__(self):
        # Add a KDJ indicator
        self.kd = bt.indicators.StochasticFull(
            self.data,
            period = self.p.period,
            period_dfast = self.p.period_dfast,
            period_dslow = self.p.period_dslow,
        )
        
        self.l.K = self.kd.percD
        self.l.D = self.kd.percDSlow
        self.l.J = self.K*3 - self.D*2

class KDJStrategy(bt.Strategy):
    params = (
        ('period', 9),
        ('period_dfast', 3),
        ('period_dslow', 3),
    )
    
        
    def __init__(self):
        
        # use self defind a KDJ indicator
        self.kd = KDJ(
            self.data0,
            period = self.p.period,
            period_dfast = self.p.period_dfast,
            period_dslow = self.p.period_dslow,
        )
    
        self.crossover = bt.indicators.CrossOver(self.kd.K, self.kd.D, plot=False)
        #self.above = bt.And(self.macd.macd>0.0, self.macd.macdsignal>0.0)
        
        self.buy_signal = (self.crossover==1)
        self.sell_signal = (self.crossover==-1)
        # To keep track of pending orders
        self.order = None
        
        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            # Write down: no pending order
            self.order = None

    def next(self):
        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return
        
        # Check if we are in the market
        if not self.position:
            # Not yet ... we MIGHT BUY if ...
            if self.buy_signal[0]:
                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy()
        else:
            # Already in the market ... we might sell
            if self.sell_signal[0]:
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
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, 'testdata/stocklist.csv')
    if args.all:
        stocklist = pd.read_csv(datapath,index_col=0,parse_dates=True)
        profitValue = 0
        lossValue = 0
        for ts_code in stocklist['ts_code']:
            print(ts_code[0:6])
            mydatapath = os.path.join(modpath, 'testdata/day/'+ts_code[0:6]+'.csv')
            if not os.path.exists(mydatapath):
                print(mydatapath + ' not exists,continue!!!')
                continue

            dataframe = pd.read_csv(mydatapath,index_col=0,parse_dates=True)
            if dataframe.empty:
                continue
            dataframe['openinterest'] = 0
            data = bt.feeds.PandasData(dataname=dataframe)
            cerebro = bt.Cerebro()
            cerebro.adddata(data,name = ts_code)
            cerebro.addstrategy(KDJStrategy)
            cerebro.broker.setcash(100000.0)
            cerebro.broker.setcommission(0.0005)
            cerebro.broker.set_coc(True)
            cerebro.addsizer(bt.sizers.AllInSizerInt, percents=99)
            # cerebro.addanalyzer(bt.analyzers.SQN)
            print('Starting Portfolio Value: {:.2f}'.format(cerebro.broker.getvalue()))
            begincash = cerebro.broker.getvalue()
            cerebro.run()
            #cerebro.plot()
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
        cerebro.addstrategy(KDJStrategy)
        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(0.0005)
        cerebro.broker.set_coc(True)
        cerebro.addsizer(bt.sizers.AllInSizerInt, percents=99)
        cerebro.addanalyzer(bt.analyzers.SQN)
            
        print('Starting Portfolio Value: {:.2f}'.format(cerebro.broker.getvalue()))
        cerebro.run()
        cerebro.plot()
        print('Ending Portfolio Value: {:.2f}'.format(cerebro.broker.getvalue()))

if __name__ == '__main__':
    runstrat()