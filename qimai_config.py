# -*- coding: utf-8 -*-

#mysql_host = '10.153.116.8'
#mysql_host = '127.0.0.1'
#mysql_port = 3306
#mysql_user = 'root'
#mysql_password = '123456'
#mysql_db = 'crawler'

# gc


### monogo config
#mongo_host = '47.98.213.195'
mongo_host = '10.153.80.26'
mongo_port = 27017
mongo_user = 'gc'
mongo_password = 'mKy56RYn2'
mongo_db = 'gc'

# 现在为避免麻烦，先全量覆盖，不保存历史排行记录
collection_game = 'qimai_game'
collection_software = 'qimai_software'
collection_keywords = 'qimai_search_index'

'''
collection_game = 'qimai_game'
collection_software = 'qimai_software'
collection_keywords = 'qimai_search_index'
'''


# qimai config
user_list = [['19802021272', 'cmic123*']]
start_url = 'https://www.qimai.cn/'
login_url = "https://www.qimai.cn/account/signin/r/%2F"





# explorer config
firefox_driver_path = "D:\\Program Files\\Mozilla Firefox\\firefox.exe"
# proxy_list = [["ip", port]]
#firefox_driver_path = "D:\\Program Files\\firefox\\geckodriver.exe"




# 输出文件及日志文件配置
result_dir = './result'
log_dir = './logs'
log_file = 'spider_log'

