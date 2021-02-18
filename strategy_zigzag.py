from backtrader.feeds.pandafeed import PandasData
import backtrader as bt
import datetime

import pandas as pd
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])
import argparse
import common
import math
import multiprocessing

modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
datapath = os.path.join(modpath, 'testdata/stocklist.csv')
class ZigzagStrategy(bt.Strategy):
    params = (
        ('peak',0.0),
        ('valley',0.0),
        ('peak_index',0),
        ('valley_index',0),
        ('lastprice',0.0),
        ('stock_name',''),
        ('fakevalley',True),
        ('printlog',True),
        ('up_kline',False),
        ('maxcpus',12),
        ('buylenth',0),
        ('forcesell',False)
    )
    
    def log(self, txt, dt=None):
        if(self.p.printlog):
            ''' Logging function fot this strategy'''
            dt = dt or self.datas[0].datetime.date(0)
            if(dt.isoformat() == '2018-10-11'):
                print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        
        self.datalow = self.data0.low
        self.dataclose = self.data0.close
        self.dataopen = self.data0.open

        self.zigzag = bt.ind.ZigZag(self.data, plotname='ZZ')
        self.zigzag_buy = False
        self.zigzag_sell = False

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
        # zigzag_buy = (self.datalow[0] < self.p.valley * 1.03)  and (self.datalow[0] > self.p.valley) and self.p.up_kline
        # zigzag_sell = (self.datalow[0] < self.p.valley) or (self.dataclose[0] > self.p.lastprice * 1.15)
        if(not math.isnan(self.zigzag.zigzag_valley[0])):
            self.p.buylenth = len(self)
            self.p.valley = self.zigzag.zigzag_valley[0]
            self.log('self.p.valley = %.4f' % self.zigzag.zigzag_valley[0])
            self.p.fakevalley = False
            updata = self.dataclose[0] if self.dataopen[0] > self.dataclose[0] else self.dataopen[0]
            self.p.valley_index = len(self)
            # print('updata = %.2f' % updata)
            if ((updata - self.datalow[0])/self.datalow[0]) > 0.02:
                self.p.up_kline = True
            else:
                self.p.up_kline = False
            
            if (self.position):
                self.p.forcesell = True

        if(not math.isnan(self.zigzag.zigzag_peak[0])):
            self.p.peak = self.zigzag.zigzag_peak[0]
            self.p.peak_index = len(self)
            self.log('self.p.peak = %.4f' % self.zigzag.zigzag_peak[0])
        if(self.datalow[0] < self.p.fakevalley):
            self.p.fakevalley = True

        if((self.p.peak_index) and (self.p.valley_index)):

            self.zigzag_buy = (self.datalow[0] < self.p.valley * 1.03) and (self.datalow[0] > self.p.valley) and self.p.up_kline and ((self.p.peak_index - self.p.valley_index)>0)
            self.zigzag_sell = (self.datalow[0] < self.p.valley) or (self.dataclose[0] > self.p.lastprice * 1.15) or self.p.forcesell
        if self.order:
            return
        
        # Check if we are in the market
        if not self.position:
            # Not yet ... we MIGHT BUY if ...
            if self.zigzag_buy:
                self.log('buy self.p.peak = %.2f self.datalow[0] = %.2f' % (self.p.valley,self.datalow[0]))
                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy()
                
                self.p.lastprice = self.dataclose[0]
        else:
            # Already in the market ... we might sell
            if self.zigzag_sell:
                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()
                self.p.forcesell = False

    def stop(self):
        if ((self.datalow[0] < self.p.valley * 1.03)  and (self.datalow[0] > self.p.valley) and (not self.p.fakevalley)):
            with open('attention.txt','a') as f:
                if(self.p.up_kline):
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
    mydatapath = os.path.join(modpath, 'testdata/day/'+ts_code[0:6]+'.csv')
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
    data = bt.feeds.PandasData(dataname=dataframe,
    fromdate=datetime.datetime(2018, 1, 1))
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
    # lock.acquire()
    if(begincash > endcash):
        return (ts_code + ' loss!' + ' ' + str(round(endcash,2)))
    else:
        return (ts_code + ' profit!' + ' ' + str(round(endcash,2)))
        # profitValue = profitValue +1
        # logger.logerr(ts_code[0:6] + 'profit!')
    # lock.release()

def runstrat(args=None):
    args = parse_args(args)
    logger = common.MyLog(__name__,__file__)
    logger.instance()
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    mydatafeed = common.MyDatafeed(datacls=PandasData,strategycls=ZigzagStrategy,args=args,logger=logger,modpath=modpath)
    mydatafeed.run()
    # args = parse_args(args)

    # logger = common.MyLog(__name__,__file__)
    # logger.instance()
    # start_time = str(datetime.datetime.now())
    # # modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    # # datapath = os.path.join(modpath, 'testdata/stocklist.csv')
    # global datapath
    # print(datapath)
    # stocklist = pd.read_csv(datapath,index_col=0,parse_dates=True)
    # # lock = multiprocessing.Lock()
    # if args.all:
    #     profitValue = 0
    #     lossValue = 0
    #     if(args.mp):
    #         with multiprocessing.Pool() as pool:
    #             for s in pool.imap_unordered(all_stratepy,stocklist['ts_code'],chunksize=10):
    #                 logger.logerr(s)
    #                 if(s is not None):
    #                     if 'loss' in s:
    #                         lossValue += 1
    #                     else :
    #                         profitValue += 1
    #     else:
    #         for ts_code in stocklist['ts_code']:
    #             s = all_stratepy(ts_code)
    #             logger.logerr(s)
    #             if(s is not None):
    #                 if 'loss' in s:
    #                     lossValue += 1
    #                 else :
    #                     profitValue += 1
    #     logger.logerr('profit:' + str(profitValue) + ' loss:' + str(lossValue))
    # else:
    #     if not args.s is None:
    #         datapath = os.path.join(modpath, 'testdata/xueqiu/',args.s+'.csv')
    #     else:
    #         datapath = os.path.join(modpath,'testdata/bt_csv_from_toshare.csv')
    #     print(datapath)
    #     if not os.path.exists(datapath):
    #         print(datapath + ' not exists,pls use the correct path!!!')
    #         sys.exit(0)
    #     dataframe = pd.read_csv(datapath,index_col=0,parse_dates=True)
    #     if dataframe.shape[0] < 10:
    #         print('dataframe too short')
    #         sys.exit(0)
    #     dataframe['openinterest'] = 0
    #     data = bt.feeds.PandasData(dataname=dataframe,
    #         fromdate=datetime.datetime(2018, 1, 1),
    #         # todate=datetime.datetime(2019, 12, 31),
    #     )
    #     cerebro = bt.Cerebro()
    #     cerebro.adddata(data)
    #     cerebro.addstrategy(ZigzagStrategy)
    #     cerebro.broker.setcash(100000.0)
    #     # cerebro.broker.setcommission(0.0005)
    #     cerebro.broker.set_coc(True)
    #     cerebro.addsizer(bt.sizers.AllInSizerInt, percents=99)
    #     cerebro.addanalyzer(bt.analyzers.SQN)
            
    #     print('Starting Portfolio Value: {:.2f}'.format(cerebro.broker.getvalue()))
    #     cerebro.run()
    #     cerebro.plot(style = 'candle',barup = 'red',bardown = 'green')
    #     print('Ending Portfolio Value: {:.2f}'.format(cerebro.broker.getvalue()))
    # print('start_time = ' + start_time + ' end time =' + str(datetime.datetime.now()))


if __name__ == '__main__':
    runstrat()
