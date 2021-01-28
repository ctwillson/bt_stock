import backtrader as bt
import datetime

import pandas as pd
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])
import argparse
from mylogs import mylog
import math

class ZigzagStrategy(bt.Strategy):
    params = (
        ('peak',0.0),
        ('valley',0.0),
        ('lastprice',0.0),
        ('stock_name',''),
        ('fakevalley',True),
        ('printlog',True),
    )
    
    def log(self, txt, dt=None):
        if(self.p.printlog):
            ''' Logging function fot this strategy'''
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        
        self.datalow = self.data0.low
        self.dataclose = self.data0.low

        self.zigzag = bt.ind.ZigZag(self.data.low, plotname='ZZ')

        # To keep track of pending orders
        self.order = None
        
    # def prenext(self):
    #     print("prenext")
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, %.2f' % order.executed.price)
            elif order.issell():
                self.log('SELL EXECUTED, %.2f' % order.executed.price)

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def next(self):
        # print('data len= ' + str(len(self.data0)))
        # Check if an order is pending ... if yes, we cannot send a 2nd one

        # print('self.p.valley = ' + str(self.p.valley * 0.9))
        # print('self.p.valley * 0.97 = %.4f ' % float(self.p.valley) * 0.97)
        zigzag_buy = (self.datalow[0] < self.p.valley * 1.03)  and (self.datalow[0] > self.p.valley)
        zigzag_sell = (self.datalow[0] < self.p.valley) or (self.dataclose[0] > self.p.lastprice * 1.15)
        if(not math.isnan(self.zigzag.zigzag_valley[0])):
            self.p.valley = self.zigzag.zigzag_valley[0]
            self.p.fakevalley = False
            # print(self.zigzag.zigzag_valley[0])


        if(not math.isnan(self.zigzag.zigzag_peak[0])):
            self.p.peak = self.zigzag.zigzag_peak[0]
            # print(self.zigzag.zigzag_peak[0])
        if(self.datalow[0] < self.p.fakevalley):
            self.p.fakevalley = True
        if self.order:
            return
        
        # Check if we are in the market
        if not self.position:
            # Not yet ... we MIGHT BUY if ...
            if zigzag_buy:
                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy()
                
                self.p.lastprice = self.dataclose[0]
        else:
            # Already in the market ... we might sell
            if zigzag_sell:
                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()

    def stop(self):
        if ((self.datalow[0] < self.p.valley * 1.03)  and (self.datalow[0] > self.p.valley) and (not self.p.fakevalley)):
            with open('attention.txt','a') as f:
                f.write(self.datas[0].datetime.date(0).isoformat() + str(self.p.stock_name) + '\n')



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
            cerebro.addstrategy(ZigzagStrategy,stock_name = ts_code)
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
        cerebro.addstrategy(ZigzagStrategy)
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
