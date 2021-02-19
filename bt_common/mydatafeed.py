import sys
sys.path.append('../')
import backtrader as bt
import os
import datetime
import pandas as pd
import multiprocessing

class MyDatafeed(object):
    def __init__(self,datacls,strategycls,args,logger,modpath):
        # self.ts_code = ts_code
        # self.plot = plot
        self.datacls = datacls
        self.strategycls = strategycls
        self.args = args
        self.logger = logger
        self.modpath = modpath
    def _all_stratepy(self,ts_code):
        print(ts_code[0:6])
        mydatapath = os.path.join(self.modpath, 'testdata/xueqiu/'+ts_code[0:6]+'.csv')
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
        data = self.datacls(dataname=dataframe,
            fromdate=datetime.datetime(2018, 1, 1))
        cerebro = bt.Cerebro()
        cerebro.adddata(data,name = ts_code)
        cerebro.addstrategy(self.strategycls,stock_name = ts_code,datalen=dataframe.loc['2018-01-01':].shape[0])
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
    def run(self):
        # args = parse_args(args)

        # logger = mylog.MyLog(__name__,__file__)
        # logger.instance()
        start_time = str(datetime.datetime.now())
        # modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
        datapath = os.path.join(self.modpath, 'testdata/stocklist.csv')
        # global datapath
        stocklist = pd.read_csv(datapath,index_col=0,parse_dates=True)
        # lock = multiprocessing.Lock()
        if self.args.all:
            profitValue = 0
            lossValue = 0
            if(self.args.mp):
                with multiprocessing.Pool() as pool:
                    for s in pool.imap_unordered(self._all_stratepy,stocklist['ts_code'],chunksize=10):
                        self.logger.logerr(s)
                        if(s is not None):
                            if 'loss' in s:
                                lossValue += 1
                            else :
                                profitValue += 1
            else:
                for ts_code in stocklist['ts_code']:
                    s = self._all_stratepy(ts_code)
                    self.logger.logerr(s)
                    if(s is not None):
                        if 'loss' in s:
                            lossValue += 1
                        else :
                            profitValue += 1
            self.logger.logerr('profit:' + str(profitValue) + ' loss:' + str(lossValue))
        else:
            if not self.args.s is None:
                datapath = os.path.join(self.modpath, 'testdata/xueqiu/',self.args.s+'.csv')
            else:
                datapath = os.path.join(self.modpath,'testdata/bt_csv_from_toshare.csv')
            print(datapath)
            if not os.path.exists(datapath):
                print(datapath + ' not exists,pls use the correct path!!!')
                sys.exit(0)
            dataframe = pd.read_csv(datapath,index_col=0,parse_dates=True)
            if dataframe.shape[0] < 10:
                print('dataframe too short')
                sys.exit(0)
            dataframe['openinterest'] = 0
            data = self.datacls(dataname=dataframe,
                fromdate=datetime.datetime(2018, 1, 1),
                # todate=datetime.datetime(2019, 12, 31),
            )
            cerebro = bt.Cerebro()
            cerebro.adddata(data)
            cerebro.addstrategy(self.strategycls,datalen=dataframe.loc['2018-01-01':].shape[0])
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