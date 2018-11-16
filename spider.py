#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import json
import random
import time
import traceback
import urlparse
import os
import traceback
import datetime

#import MySQLdb
from pymongo import MongoClient
from lxml import etree
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

import qimai_config
import log_utils

log = log_utils.log_utils()


class QimaiSpider(object):
    def __init__(self):
        self.cur_date_url = time.strftime("%Y-%m-%d")
        self.cur_date = time.strftime("%Y%m%d")

        # 排行榜现在只能获取一周前的数据
        rank_date = datetime.date.today() # + datetime.timedelta(days=-8)
        self.rank_date_url_suffix = rank_date.strftime('%Y-%m-%d')

        
        #自定义日期
        # self.cur_date_url = "2018-10-05"
        # self.cur_date = "20181005"
        self.start_url = qimai_config.start_url
        self.login_url = qimai_config.login_url

        self.firefox_options = webdriver.FirefoxOptions()
        #self.firefox_options.add_argument("-headless")
        self.firefox_options.set_headless()

        prepath = qimai_config.result_dir + '/' + self.cur_date
        if not os.path.exists(prepath):
            os.makedirs(prepath)
        self.data_file = codecs.open('%s/search_index_%s.json' % (prepath, self.cur_date), mode='w', encoding='utf-8')
        self.app_rank_game_file = codecs.open('%s/app_rank_game_%s.json' % (prepath, self.cur_date), mode='w', encoding='utf-8')
        self.app_rank_software_file = codecs.open('%s/app_rank_software_%s.json' % (prepath, self.cur_date), mode='w', encoding='utf-8')


        self.client = MongoClient(qimai_config.mongo_host, qimai_config.mongo_port)
        self.db = self.client[qimai_config.mongo_db]
        self.db.authenticate(qimai_config.mongo_user, qimai_config.mongo_password)

        # 现在为避免麻烦，先全量覆盖，不保存历史排行记录
        self.collection_game = self.db[qimai_config.collection_game]
        self.collection_software = self.db[qimai_config.collection_software]
        self.collection_keywords = self.db[qimai_config.collection_keywords]
        self.collection_keywords_bkf = self.db[qimai_config.collection_keywords + '_' + self.cur_date]





    def __del__(self):
        self.data_file.close()
        self.app_rank_game_file.close()
        self.app_rank_software_file.close()


    #####################
    # 连接到七麦网站，并登陆
    #####################
    def chrome_func(self, login_enabled=True):
        # driver = webdriver.Chrome(executable_path='E:\chrome_driver\chromedriver.exe')
        # chrome_options=self.chrome_options)
        # proxy = random.choice(qimai_config.proxy_list)
        # profile = FirefoxProfile()
        # profile.set_preference("network.proxy.type", 1)
        # profile.set_preference("network.proxy.http", proxy[0])
        # profile.set_preference("network.proxy.http_port", proxy[1])
        # profile.set_preference("network.proxy.share_proxy_settings", True)
        # driver = webdriver.Firefox(firefox_profile=profile, executable_path="E:\\firefox\\geckodriver.exe")
        #driver = webdriver.Firefox(executable_path=qimai_config.firefox_driver_path,\
        #                           firefox_options=self.firefox_options)

        driver = webdriver.Firefox(firefox_options=self.firefox_options)



        # 先打开七麦首页查看是否网络可以连通
        driver.get(self.start_url)
        driver.set_page_load_timeout(40)
        first_page_bool = self.wait_page_load(driver, By.CLASS_NAME, 'sign')
        if first_page_bool:
            log.info( "Get start url successfully!!!")
        else:
            log.info( "Wait to get start url timeout! url: %s" % self.start_url)
            return
        if not login_enabled:
            return driver

        ######### new added cookies ############
         
        f = codecs.open(qimai_config.cookie_path, mode='r', encoding = 'utf-8')
        cookies = json.loads(f.read())
        for cookie in cookies:
            driver.add_cookie({
                'name':cookie['name'],
                'value':cookie['value']
                }
            )

        f.close()
        
        ######### new added cookies ############

        # 打开登陆页面
        driver.get(self.login_url)
        driver.set_page_load_timeout(50)
        login_page_bool = self.wait_page_load(driver, By.CLASS_NAME, 'ivu-form-item-content')
        if login_page_bool:
            log.info( "Get login page successfully!!!" )
        else:
            log.info( "Wait to get login page timeout! url: %s" % self.login_url )
            return


        # 登陆
        user = random.choice(qimai_config.user_list)
        login_name = user[0]
        login_password = user[1]
        driver.find_element_by_xpath("//input[@name='username']").send_keys(login_name)
        driver.find_element_by_xpath("//input[@name='password']").send_keys(login_password)
        driver.find_element_by_xpath(
            "//div[@class='ivu-form-item-content']/button[@class='ivu-btn ivu-btn-primary']").click()
        login_submit_bool = self.wait_page_load(driver, By.CLASS_NAME, 'more-dynamic')
        if login_submit_bool:
            log.info( "Login submit successfully!!!" )
        else:
            log.info( "Wait to login submit timeout!")
            return


        
        # driver.save_screenshot('after_login.png')
        return driver





    #########################
    # 七麦热词
    #########################
    def get_search_index(self, driver):
        search_index_url = "https://www.qimai.cn/trend/keywordRank"
        driver.get(search_index_url)

        log.info( "document.body.scrollHeight: "),
        log.info( driver.execute_script("return document.body.scrollHeight;"))
        while int(driver.execute_script("return document.body.scrollHeight;")) < 47000:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            log.info( "document.body.scrollHeight: " )
            log.info( driver.execute_script("return document.body.scrollHeight;"))
            time.sleep(random.random() * 5)
        body = driver.page_source
        # print body
        page = etree.HTML(body)
        tr_list = page.xpath("//tbody[@class='ivu-table-tbody']/tr")

        # 备份热词数据
        self.collection_keywords_bkf.remove()
        keywords_bkf = self.collection_keywords.find()
        if keywords_bkf.count() > 0:
            self.collection_keywords_bkf.insert(keywords_bkf)
        self.collection_keywords.remove()

        
        for tr in tr_list:
            td_list = tr.xpath("./td/div")
            rank_num = td_list[0].xpath("./span/text()")[0]
            keyword = td_list[1].xpath("./a/text()")[0]
            keyword_url = urlparse.urljoin(driver.current_url, td_list[1].xpath("./a/@href")[0])
            search_index = td_list[2].xpath("./a/text()")[0]
            search_index_url = urlparse.urljoin(driver.current_url, td_list[2].xpath("./a/@href")[0])
            search_result = td_list[3].xpath("./a/text()")[0]
            search_result_url = urlparse.urljoin(driver.current_url, td_list[3].xpath("./a/@href")[0])
            first_app_name = td_list[4].xpath("./a/text()")[0]
            first_app_url = urlparse.urljoin(driver.current_url, td_list[4].xpath("./a/@href")[0])
            
            data = {"rank_num": rank_num, "keyword": keyword, "keyword_url": keyword_url,
                    "search_index": search_index, "search_index_url": search_index_url,
                    "search_result": search_result, "search_result_url": search_result_url,
                    "first_app_name": first_app_name, "first_app_url": first_app_url,
                    "cur_date": self.cur_date_url}
            
            self.data_file.write(json.dumps(data, ensure_ascii=False) + "\n")
            
            self.collection_keywords.insert_one(data)

    def get_android_app_rank(self, ):
        driver = self.chrome_func(login_enabled=False)
        try:
            self.collection_game.remove()
            game_rank_url = "https://www.qimai.cn/rank/marketRank/market/3/category/-2/date/%s" % self.rank_date_url_suffix
            self.change_app_rank_url(driver, game_rank_url, self.app_rank_game_file, self.collection_game)
            driver.quit()
        except:
            log.info( traceback.print_exc() )
            driver.quit()
        driver = self.chrome_func(login_enabled=False)
        try:
            self.collection_software.remove()
            software_rank_url = "https://www.qimai.cn/rank/marketRank/market/3/category/-1/date/%s" % self.rank_date_url_suffix
            self.change_app_rank_url(driver, software_rank_url, self.app_rank_software_file, self.collection_software)
            driver.quit()
        except:
            log.info( traceback.print_exc() )
            driver.quit()

    def change_app_rank_url(self, driver, rank_url, file_name, collection_app):
        driver.get(rank_url)
        driver.set_page_load_timeout(15)
        game_rank_bool = self.wait_page_load(driver, By.CLASS_NAME, 'data-table')
        if not game_rank_bool:
            time.sleep(random.random() * 5)
        body = driver.page_source

        # debug
        # self.boddy = body
        
        self.get_app_info(body, driver, file_name, collection_app)

    def get_app_info(self, body, driver, app_file, collection_app):
        page = etree.HTML(body)
        tr_list = page.xpath("//table[@class='data-table']/tbody/tr")

        self.trs = tr_list
        self.pagee = page
        if(len(tr_list) == 0):
            log.info('zero tr_list')
        else:
            log.info('non-zero tr_list')
        for tr in tr_list:
            td_list = tr.xpath("./td")
            try:
                app_name = td_list[1].xpath(".//div[@class='app-info']/a/text()")[0].strip()
                app_url = td_list[1].xpath(".//div[@class='app-info']/a/@href")[0].strip()
                app_url = urlparse.urljoin(driver.current_url, app_url)
                brief_company_name = td_list[1].xpath(".//div[@class='app-info']/p[@class='company']/text()")[0].strip()
                rank_num = td_list[2].xpath(".//p[@class='num total-num']/text()")[0]
                category = td_list[3].xpath("./div/text()")[0]
                yesterday_download_num = td_list[4].xpath("./div/text()")[0]
                update_date = td_list[5].xpath("./div/text()")[0]
                company_name = td_list[6].xpath("./a/text() | ./p/text()")[0].strip()
                company_name_url = "".join(td_list[6].xpath("./a/@href"))
                if company_name_url != "":
                    company_name_url = urlparse.urljoin(driver.current_url, company_name_url)
            except IndexError, e:
                log.info('str(Exception):\t' + str(Exception))
                log.info( 'str(e):\t\t' + str(e) )
                log.info( 'repr(e):\t' + repr(e) )
                log.info( 'e.message:\t', e.message )
                log.info( 'traceback.print_exc():')
                log,info( traceback.print_exc() )
                log.info( 'traceback.format_exc():\n%s' % traceback.format_exc() )
                continue
            #app_id = self.get_packagename(app_url, collection_app)
            app_id = None
            if app_id is None:
                
                try:
                    
                    app_id = self.get_app_id(driver, app_url)
                    #query = "insert into qimai_app(app_name, app_url, package_name) values('%s','%s','%s')"
                    #self.cursor.execute(query % (app_name, app_url, app_id))
                    log.info('insert into collection')
                    collection_app.insert_one({"app_name":app_name, "app_url":app_url, "package_name":app_id})

                    time.sleep(random.random())
                except:
                    log.info( "get app id for %s failed!" % app_url)
                    app_id = ''

            else:
                log.info(app_id)
            data = {"rank_num": rank_num, "app_name": app_name, "app_url": app_url,
                    "brief_company_name": brief_company_name, "category": category,
                    "yesterday_download_num": yesterday_download_num, "update_date": update_date,
                    "company_name": company_name, "company_name_url": company_name_url,
                    "cur_date": self.cur_date_url, "app_id": app_id}
            print data
            app_file.write(json.dumps(data, ensure_ascii=False) + "\n")

    def get_app_id(self, driver, url):
        driver.get(url)
        driver.set_page_load_timeout(15)
        app_page_bool = self.wait_page_load(driver, By.CLASS_NAME, 'appid')
        if not app_page_bool:
            time.sleep(random.random() * 5)
        body = driver.page_source
        page = etree.HTML(body)
        app_id = page.xpath("//div[@class='appid']/div[@class='value']/text()")[0]
        return app_id

    @staticmethod
    def wait_page_load(driver, wait_ele, value):
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((wait_ele, value))
            )
        except WebDriverException:
            return False
        return True

    def get_packagename(self, app_url, collection_app):
        # query = "select package_name from qimai_app where app_url='%s'" % app_url
        # try:
        #     self.cursor.execute(query)
        #     result = self.cursor.fetchone()
        #     if result:
        #         return result[0]
        # except Exception as e:
        #     print e

        try:
            result = collection_app.find({"app_url":app_url})
            if result:
                return result[0]
        except Exception as e:
            log.info( e )
        return None

    def main(self):
        driver = self.chrome_func()
        
        try:
            self.get_search_index(driver)
            driver.quit()
        except:
            print traceback.print_exc()
            driver.quit()
            return
        
        self.get_android_app_rank()


if __name__ == "__main__":
    qimai = QimaiSpider()
    qimai.main()
