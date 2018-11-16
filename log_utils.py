# -*- coding: utf-8 -*-
import logging
import os
import qimai_config
from logging.handlers import TimedRotatingFileHandler

class log_utils():
    def __init__(self):
        self.logger = logging.getLogger('qimai_logger')
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')


        # 文件handler
        if not os.path.exists(qimai_config.log_dir):
            os.makedirs(qimai_config.log_dir)
        fh = logging.FileHandler(qimai_config.log_dir + '/' + qimai_config.log_file)
        fh.setLevel(logging.DEBUG)
        
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

        # 控制台handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        

        '''
        # 日分日志
        trh = TimedRotatingFileHandler(qimai_config.log_dir + '/' + qimai_config.log_file, when = 'D', encoding = 'utf-8')
        trh.setLevel(logging.DEBUG)
        trh.setFormatter(formatter)
        self.logger.addHandler(trh)
        '''

        

    def info(self, msg):
        self.logger.info(msg)
        #print(msg)
