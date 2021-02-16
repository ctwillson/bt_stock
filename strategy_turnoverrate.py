import backtrader as bt
import datetime

import pandas as pd
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])
import argparse
from mylogs import mylog
import math
import multiprocessing

modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
datapath = os.path.join(modpath, 'testdata/stocklist.csv')
class PandasDataTurnover(bt.feeds.PandasData):
    lines = ('turnoverrate',)
    params = (
        ('turnoverrate',-1),
    )
class TurnoverStrategy(bt.Strategy):
    params = (
        ('printlog',True),
        ('stock_name',''),
        ('bugsig',False),
        ('sellsig',False),
        ('fastema',12),
        ('slowema',26),
    )
    
    def log(self, txt, dt=None):
        if(self.p.printlog):
            ''' Logging function fot this strategy'''
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        
        self.datalow = self.data0.low
        self.dataclose = self.data0.close
        self.dataopen = self.data0.open
        self.dataturnoverrate = self.data0.turnoverrate

        # To keep track of pending orders
        self.order = None
        
            # self.fastema = bt.ind.EMA(self.data.turnoverrate,period=self.p.fastema)
            # self.slowema = bt.ind.EMA(self.data.turnoverrate,period=self.p.slowema)
            # self.crossover = bt.indicators.CrossOver(self.fastema, self.slowema, plot=False)
        self.buysig = False
        self.sellsig = True
        # self.buy_signal = self.crossover == 1
        # self.sell_signal = self.crossover == -1
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
        self.buysig = self.dataturnoverrate[0] > (2 * self.dataturnoverrate[-1])
        if self.order:
            return
        
        # Check if we are in the market
        if not self.position:
            # Not yet ... we MIGHT BUY if ...
            if self.buysig:
                self.log('self.dataturnoverrate = %.2f' % self.dataturnoverrate[0])
                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy()
                self.sellsig = True
        else:
            # Already in the market ... we might sell
            if self.sellsig:
                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()
                self.sellsig = False

    def stop(self):
        with open('attention_turnover.txt','a') as f:
            if(self.dataturnoverrate[0] > (2 * self.dataturnoverrate[-1])):
                f.write(self.datas[0].datetime.date(0).isoformat() + ' ' + str(self.p.stock_name) + '\n')



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

    parser.add_argument('--mp', required=False, action='store_true',
                        help='wheather use multiprocessing')
    return parser.parse_args(pargs)
def all_stratepy(ts_code):
    print(ts_code[0:6])
    global modpath
    mydatapath = os.path.join(modpath, 'testdata/xueqiu/'+ts_code[0:6]+'.csv')
    if not os.path.exists(mydatapath) :
        print(mydatapath + ' not exists,continue!!!')
        return

    dataframe = pd.read_csv(mydatapath,index_col=0,parse_dates=True)
    if dataframe.empty:
        return
    if dataframe.shape[0] < 10:
        print('dataframe too short')
        return
    dataframe['openinterest'] = 0
    data = PandasDataTurnover(dataname=dataframe,
        fromdate=datetime.datetime(2018, 1, 1))
    cerebro = bt.Cerebro()
    cerebro.adddata(data,name = ts_code)
    cerebro.addstrategy(TurnoverStrategy,stock_name = ts_code)
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
    # lock.acquire()
    if(begincash > endcash):
        return (ts_code + ' loss!' + ' ' + str(round(endcash,2)))
    elif (begincash < endcash):
        return (ts_code + ' profit!' + ' ' + str(round(endcash,2)))
    else:
        return None
        # profitValue = profitValue +1
        # logger.logerr(ts_code[0:6] + 'profit!')
    # lock.release()

def runstrat(args=None):
    args = parse_args(args)

    logger = mylog.MyLog(__name__,__file__)
    logger.instance()
    start_time = str(datetime.datetime.now())
    # modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    # datapath = os.path.join(modpath, 'testdata/stocklist.csv')
    global datapath
    stocklist = pd.read_csv(datapath,index_col=0,parse_dates=True)
    # lock = multiprocessing.Lock()
    if args.all:
        profitValue = 0
        lossValue = 0
        if(args.mp):
            with multiprocessing.Pool() as pool:
                for s in pool.imap_unordered(all_stratepy,stocklist['ts_code'],chunksize=10):
                    logger.logerr(s)
                    if(s is not None):
                        if 'loss' in s:
                            lossValue += 1
                        else :
                            profitValue += 1
        else:
            for ts_code in stocklist['ts_code']:
                s = all_stratepy(ts_code)
                logger.logerr(s)
                if(s is not None):
                    if 'loss' in s:
                        lossValue += 1
                    else :
                        profitValue += 1
        logger.logerr('profit:' + str(profitValue) + ' loss:' + str(lossValue))
    else:
        if not args.s is None:
            datapath = os.path.join(modpath, 'testdata/xueqiu/',args.s+'.csv')
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
        data = PandasDataTurnover(dataname=dataframe,
            fromdate=datetime.datetime(2018, 1, 1),
            # todate=datetime.datetime(2019, 12, 31),
        )
        cerebro = bt.Cerebro()
        cerebro.adddata(data)
        cerebro.addstrategy(TurnoverStrategy)
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
