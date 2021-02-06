from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])


# Import the backtrader platform
import backtrader as bt
import argparse
from mylogs import mylog
import pandas as pd
# Create a Stratey
class Doubleupkkline(bt.Strategy):
    params = (
        ('upkline_perid',3),
        ('printlog', True),
    )

    def log(self, txt, dt=None, doprint=False):
        ''' Logging function fot this strategy'''
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close
        self.datalow = self.datas[0].low
        self.dataopen = self.datas[0].open
        self.datahigh = self.datas[0].high

        self.dataclose_before = None
        self.datalow_before = None
        self.dataopen_before = None
        self.datahigh_before = None
        self.upkline_index = None
        self.buyprice = None

        # To keep track of pending orders
        self.order = None
        self.buysig = None
        self.sellsig = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                # self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
                self.buyprice = None

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # Simply log the closing price of the series from the reference
        # self.log('Close, %.2f' % self.dataclose[0])
        # take notes the second low price
        datalow2 = self.dataopen[0] if self.dataclose[0] > self.dataopen[0] else self.dataclose[0]
        # if(self.buyprice is not None):
        #     print('not none self.buyprice = %.2f' % self.buyprice)
        upkline = (datalow2 - self.datalow[0]) / self.datalow[0]
        if(upkline > 0.02):
            # when sell,we will clear the upkline_index and also the init of upkline_index
            if(self.upkline_index is None):
                self.upkline_index = len(self)
                if(not self.position):
                    self.datalow_before = self.datalow[0]
                    self.dataopen_before = self.dataopen[0]
                    self.datahigh_before = self.datahigh[0]
            else:
                if((self.datalow_before > self.datalow[0])):
                    if((not self.position)):
                        self.upkline_index = len(self)
                        self.datalow_before = self.datalow[0]
                        self.dataopen_before = self.dataopen[0]
                        self.datahigh_before = self.datahigh[0]
            if(self.upkline_index is not None):
                # if(self.datalow < self.datalow_before):
                #     self.upkline_index = len(self)
                if(0 <(len(self) - self.upkline_index) < self.p.upkline_perid):
                    tmp = True
                    for i in range(0,self.p.upkline_perid):
                        if(self.datalow[-i] < self.datalow_before):
                            tmp = False
                    self.buysig = tmp and ((self.datalow[0] - self.datalow_before) <0.03)

        if(self.buyprice is not None):
            self.log(self.buyprice)
            self.sellsig = (self.datalow[0] < self.datalow_before)  or ((self.datahigh[0] - self.buyprice)/self.buyprice > 0.1)
        if self.order:
            return

        # Check if we are in the market
        if not self.position:

            # Not yet ... we MIGHT BUY if ...
            if self.buysig:

                # BUY, BUY, BUY!!! (with all possible default parameters)
                self.log('BUY CREATE, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy()
                self.buysig = False

        else:

            if self.sellsig:
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log('SELL CREATE, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()
                self.upkline_index = None

    def stop(self):
        self.log('Ending Value %.2f' %
                 (self.broker.getvalue()), doprint=True)

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
            if dataframe.shape[0] < 10:
                print('dataframe too short')
                continue
            dataframe['openinterest'] = 0
            data = bt.feeds.PandasData(dataname=dataframe)
            cerebro = bt.Cerebro()
            cerebro.adddata(data,name = ts_code)
            cerebro.addstrategy(Doubleupkkline,stock_name = ts_code)
            cerebro.broker.setcash(100000.0)
            # cerebro.broker.setcommission(0.0005)
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
        if dataframe.shape[0] < 10:
            print('dataframe too short')
            sys.exit(0)
        dataframe['openinterest'] = 0
        data = bt.feeds.PandasData(dataname=dataframe)
        cerebro = bt.Cerebro()
        cerebro.adddata(data)
        cerebro.addstrategy(Doubleupkkline)
        cerebro.broker.setcash(100000.0)
        # cerebro.broker.setcommission(0.0005)
        cerebro.broker.set_coc(True)
        cerebro.addsizer(bt.sizers.AllInSizerInt, percents=99)
        cerebro.addanalyzer(bt.analyzers.SQN)
            
        print('Starting Portfolio Value: {:.2f}'.format(cerebro.broker.getvalue()))
        cerebro.run()
        cerebro.plot(style = 'candle',barup = 'red',bardown = 'green')
        print('Ending Portfolio Value: {:.2f}'.format(cerebro.broker.getvalue()))
    print('start_time = ' + start_time + ' end time =' + str(datetime.datetime.now()))
if __name__ == '__main__':
    runstrat()