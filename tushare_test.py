import tushare as ts
import pandas as pd
import datetime
import time
import os

now_time = pd.to_datetime(datetime.datetime.now())
start_date = '20180501'
end_date=str(now_time)[0:4]+str(now_time)[5:7]+str(now_time)[8:10]

def get_stock_list(pro):
    data = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
    if  data.empty:
        print('get stock list failed,return!')
        return
    data.to_csv('./testdata/stocklist.csv')
    stock_list = data['ts_code']
    #stock_list.to_csv('stock_list.csv')
    for ts_code in stock_list:
        while True:
            try:
                df = pro.daily(ts_code=ts_code,start_date=start_date,end_date=end_date)
                bt_df = preprocess(df,True)
                bt_df.to_csv('./testdata/day/'+ts_code[0:6]+'.csv')
                time.sleep(0.1)
            except:
                print(ts_code + "failed")
                time.sleep(2)
                continue
            break

#转换tushare data 为 backtrader data
def preprocess(df, pro=False):
    if pro:
        features=['open','high','low','close','vol','trade_date']
        # convert_datetime = lambda x:datetime.strptime(x,'%Y%m%d')
        convert_datetime = lambda x: pd.to_datetime(str(x))
        df['trade_date'] = df['trade_date'].apply(convert_datetime)
        #print(df)
        bt_col_dict = {'vol':'volume','trade_date':'datetime'}
        df = df.rename(columns=bt_col_dict)
        df = df.set_index('datetime')
        # df.index = pd.DatetimeIndex(df.index)
    else:
        features=['open','high','low','close','volume']
        df = df[features]
        df['openinterest'] = 0
        df.index = pd.DatetimeIndex(df.index)
    df = df[::-1]
    return df
if __name__ == '__main__':
    stock_list_file = 'huidingstock_list.csv'
    ts_token = os.getenv('TS_TOKEN')
    print('ts_token = ' + ts_token)
    ts.set_token(ts_token)
    pro = ts.pro_api()
    get_stock_list(pro)
    #df = pro.trade_cal(exchange='', start_date='20180901', end_date='20181001', fields='exchange,cal_date,is_open,pretrade_date', is_open='0')
    #df = pro.daily(ts_code='603160.SH',start_date='20200101',end_date='20200815')
    #df.to_csv(stock_list_file)
    #bt_df = preprocess(df,True)
    #bt_df.to_csv('bt_csv_from_toshare.csv')
    print ('done')
#print(tushare.__version__)
