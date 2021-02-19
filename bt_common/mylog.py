import logging
import logging.handlers
import os

class MyLog:
    def __init__(self,logname,filename):
        self.logname = logname
        self.filename = "mylogs/" + filename
        self.logger = logging.getLogger(self.logname)
        #logging.basicConfig(filename="logs/myapp.log", filemode="w", format="%(asctime)s %(name)s:%(levelname)s:%(message)s", datefmt="%d-%M-%Y %H:%M:%S", level=logging.INFO)
    def instance(self):
        #logger = logging.getLogger(self.logname)
        if not os.path.exists(self.filename):
            os.system(r"touch {}".format(self.filename))
        file_handler = logging.handlers.TimedRotatingFileHandler(filename=self.filename, when="MIDNIGHT",interval=1, backupCount=30)

        # 定义处理器的输出格式
        fmt_log = '%(asctime)s %(name)s %(levelname)s %(message)s'
        date_fmt = '%Y%m%d %H:%M:%S'
        formatter = logging.Formatter(fmt=fmt_log, datefmt=date_fmt)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
       # return self.logger
    def loginfo(self,message):
    #logging.debug('This is a debug message')
        self.logger.info(message)

    def logerr(self,message):
        self.logger.error(message)


if __name__ == '__main__':
    logger = MyLog(__name__,"test.log")
    logger.instance()
    logger.logerr('This is an error message')

    #logging.warning('This is a warning message')
    #logging.error('This is an error message')
    #logging.critical('This is a critical message')
