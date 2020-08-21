from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])

# Import the backtrader platform
import backtrader as bt
import pandas as pd

# Create a Stratey
class TestStrategy(bt.Strategy):

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders
        self.order = None

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
        # Simply log the closing price of the series from the reference
        self.log('Close, %.2f' % self.dataclose[0])

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return
#需要理解数组下标的含义
        # Check if we are in the market
        if not self.position:

            # Not yet ... we MIGHT BUY if ...
            if self.dataclose[0] < self.dataclose[-1]:
                    # current close less than previous close

                    if self.dataclose[-1] < self.dataclose[-2]:
                        # previous close less than the previous close

                        # BUY, BUY, BUY!!! (with default parameters)
                        self.log('BUY CREATE, %.2f' % self.dataclose[0])

                        # Keep track of the created order to avoid a 2nd order
                        self.order = self.buy()

        else:

            # Already in the market ... we might sell
            if len(self) >= (self.bar_executed + 5):
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log('SELL CREATE, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()


if __name__ == '__main__':




    # Datas are in a subfolder of the samples. Need to find where the script is
    # because it could have been called from anywhere
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, 'testdata/stocklist.csv')
    print (datapath)

    # Create a Data Feed
#    data = bt.feeds.YahooFinanceCSVData(
#        dataname=datapath,
#        # Do not pass values before this date
#        fromdate=datetime.datetime(2000, 1, 1),
        # Do not pass values before this date
#        todate=datetime.datetime(2000, 12, 31),
        # Do not pass values after this date
#        reverse=False)
    stocklist = pd.read_csv(datapath,index_col=0,parse_dates=True)
    for ts_code in stocklist['ts_code']:
        mydatapath = os.path.join(modpath, 'testdata/day/'+ts_code[0:6]+'.csv')
        if not os.path.exists(mydatapath) :
            print(mydatapath + ' not exists,continue!!!')
            continue
        dataframe = pd.read_csv(mydatapath,index_col=0,parse_dates=True)
        dataframe['openinterest'] = 0
        # Create a cerebro entity
        cerebro = bt.Cerebro()
        # Add a strategy
        cerebro.addstrategy(TestStrategy)
        
        data = bt.feeds.PandasData(dataname=dataframe
        )
        # Add the Data Feed to Cerebro
        cerebro.adddata(data)

        # Set our desired cash start
        cerebro.broker.setcash(100000.0)

        # Print out the starting conditions
        print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

        # Run over everything
        cerebro.run()

        # Print out the final result
        print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
        #cerebro.plot()
    print('all stock backtrade done!!!')
