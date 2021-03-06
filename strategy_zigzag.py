from backtrader.feed import DataClone
from backtrader.feeds.pandafeed import PandasData
import backtrader as bt
import datetime

import pandas as pd
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])
import argparse
import bt_common
import math
import csv

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
        ('datalen',0),
        ('fakevalley',True),
        ('printlog',False),
        # ('up_kline',False),
        ('maxcpus',12),
        ('buylenth',0),
        ('forcesell',False)
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

        self.zigzag = bt.ind.ZigZag(self.data, plotname='ZZ',datalen = self.p.datalen)
        self.zigzag_buy = False
        self.zigzag_sell = False

        self.zigzagvalley_list = []
        self.up_kline = []
        self.today_upkline = False

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
        updata = self.dataclose[0] if self.dataopen[0] > self.dataclose[0] else self.dataopen[0]
        # print('updata = %.2f' % updata)
        if ((updata - self.datalow[0])/self.datalow[0]) > 0.02:
            self.today_upkline = True
        else:
            self.today_upkline = False
        if((self.p.peak_index) and (self.p.valley_index)):
            self.zigzag_buy = abs(self.datalow[0] - self.p.valley) <= 0.05 and 15>=(len(self)-self.p.valley_index)>=2 and (not self.p.fakevalley)
            # self.zigzag_buy = (self.datalow[0] < self.p.valley * 1.03) and (self.datalow[0] > self.p.valley) and self.up_kline[-1] and ((self.p.peak_index - self.p.valley_index)>0)
            self.zigzag_sell = (self.datalow[0] < self.p.valley) or (self.dataclose[0] > self.p.lastprice * 1.15) or self.p.forcesell
        if(not math.isnan(self.zigzag.zigzag_valley[0])):
            self.p.buylenth = len(self)
            self.p.valley = self.zigzag.zigzag_valley[0]
            self.log('self.p.valley = %.4f' % self.zigzag.zigzag_valley[0])
            self.zigzagvalley_list.append(self.zigzag.zigzag_valley[0])
            self.p.fakevalley = False
            updata = self.dataclose[0] if self.dataopen[0] > self.dataclose[0] else self.dataopen[0]
            self.p.valley_index = len(self)
            # print('updata = %.2f' % updata)
            if ((updata - self.datalow[0])/self.datalow[0]) > 0.015:
                self.up_kline.append(True)
            else:
                self.up_kline.append(False)
            
            if (self.position):
                self.p.forcesell = True

        if(not math.isnan(self.zigzag.zigzag_peak[0])):
            self.p.peak = self.zigzag.zigzag_peak[0]
            self.p.peak_index = len(self)
            self.log('self.p.peak = %.4f' % self.zigzag.zigzag_peak[0])
        if(self.datalow[0] < self.p.valley):
            self.p.fakevalley = True

        # if((self.p.peak_index) and (self.p.valley_index)):

        #     self.zigzag_buy = (self.datalow[0] < self.p.valley * 1.03) and (self.datalow[0] > self.p.valley) and self.p.up_kline and ((self.p.peak_index - self.p.valley_index)>0)
        #     self.zigzag_sell = (self.datalow[0] < self.p.valley) or (self.dataclose[0] > self.p.lastprice * 1.15) or self.p.forcesell
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
        if (len(self.zigzagvalley_list) >= 3):
            # TODO: need optimize
            if ((self.datalow[0] < self.p.valley * 1.03)  and (self.datalow[0] > self.p.valley) and (not self.p.fakevalley)) or (abs(self.zigzagvalley_list[-1] - self.zigzagvalley_list[-2])<0.05 and 0<(self.dataclose[0] - self.zigzagvalley_list[-1])/self.zigzagvalley_list[-1] < 0.03):
                with open(modpath + '/mylogs/attention/zg.csv', "a", newline='') as file:
                    csv_file = csv.writer(file)
                    datas = [[self.datas[0].datetime.date(0),str(self.p.stock_name),self.p.valley]]
                    csv_file.writerows(datas)
            if ((abs(self.datalow[0] - self.p.valley) <= 0.05)  and (self.datalow[0] > self.p.valley) and (not self.p.fakevalley)) or (abs(self.zigzagvalley_list[-1] - self.zigzagvalley_list[-2])<0.05 and 0<(self.dataclose[0] - self.zigzagvalley_list[-1])/self.zigzagvalley_list[-1] < 0.03):

                with open('attention.txt','a') as f:
                    if(self.up_kline[-1] or (self.today_upkline) or self.up_kline[-2]):
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

def runstrat(args=None):
    args = parse_args(args)
    logger = bt_common.MyLog(__name__,__file__)
    logger.instance()
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    # print(datetime.date.today())
    # df = pd.DataFrame(columns=['ts_code','last_zg'])
    # df.to_csv('./mylogs/attention/zg.csv',index=False)
    # print(modpath + '/mylogs/attention/zg.csv')
    if(not os.path.exists(modpath + '/mylogs/attention/zg.csv')):
        with open(modpath + './mylogs/attention/zg.csv','w') as f:
            csv_write = csv.writer(f)
            csv_head = ['datetime','ts_code','last_zg']
            csv_write.writerow(csv_head)
    mydatafeed = bt_common.MyDatafeed(datacls=PandasData,strategycls=ZigzagStrategy,args=args,logger=logger,modpath=modpath)
    mydatafeed.run()


if __name__ == '__main__':
    runstrat()
