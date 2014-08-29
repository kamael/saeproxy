# -*- coding: utf-8 -*-

import os
import time
import re
import sqlite3
import requests
import threading
db_lock = threading.Lock()  # 插入数据用锁

import fetch
from fetch_tools import curl_get, tuple_to_dict


class ProxyHost:

    """
    储存和更新proxy列表
    proxy列表存放在名为 proxytable 的数据库里
    proxy列表形式为：  dict = { "host": ip,
                                "port": port,
                                "protocol": [socks4|socks5|http|https],
                                "anony": [DP|AP|TP|HAP|UN],# (混淆代理，匿名代理，透明代理，高匿名代理, 未知)
                                "speed": time, #访问测试站的时间 http://example.com, 未知则设置 1001, 连接失败则设置 1002
                                }
                    proxy_list = [dict1, dict2, ...]

    usage:
        phost = ProxyHost()
        lists = phost.get_all() # [dict1, dict2, ...]

    API:
        db_select_where     自定义的where语句，db 结构和 dict 一致
        get_all             获取所有代理
        get_anony           获取匿名代理，参数为 [DP|AP|TP|HAP|UN] -> (混淆代理，匿名代理，透明代理，高匿名代理,未知)
        get_faster          获取访问速度比参数更快的代理，比如 get_faster(3) 表示获取响应速度在 3秒以内的代理
        get_by              获取限制条件的代理 比如 get_by(protocol="http", anony="AP")
        run_plan            运行计划任务，抓取代理，测试代理等。

    """

    def __init__(self, generate=False):
        # 添加函数名称在这里，函数体写在同目录下的fetch.py 文件中。
        self.func_list = ["fetch_proxies_org", "fetch_letushide"]
        # func is a function which get proxies from page
        # and return as [(x, x, x, x, x), ...] means (host, port, protocol,
        # anony, speed)

        self.path = os.path.dirname(os.path.abspath(__file__))
        self.db = os.path.join(self.path, 'proxylist.db')
        self.conn = sqlite3.connect(self.db)

        self.__create_proxytable()

        # 计划任务
        if generate:
            self.run_func_list()
            self.update("http://example.com")

    def db_select_where(self, where_str):
        # db_select("anony = 'DP'")
        select_str = "select * from proxytable where " + where_str
        # print select_str
        c = self.conn.cursor()
        try:
            c.execute(select_str)
        except:
            print "select error in where ", where_str
            return []

        proxy_list = self.__seq_to_dictlist(c.fetchall())
        return proxy_list

    def get_all(self):
        # get all
        return self.db_select_where("1")

    def get_work(self):
        return self.db_select_where("speed < 1000")

    def get_anony(self, anony):
        return self.db_select_where("anony = '" + anony + "'")

    def get_faster(self, second):
        # get_faster(3)
        return self.db_select_where("speed < " + str(second))

    def get_by(self, protocol=None, anony=None, faster=None):
        where_str = []
        if protocol:
            where_str.append("protocol = '" + protocol + "'")
        if anony:
            where_str.append("anony = '" + anony + "'")
        if faster:
            where_str.append(" and speed < " + str(faster))

        where = " and ".join(where_str)
        return self.db_select_where(where)

    def __create_proxytable(self):
        c = self.conn.cursor()
        c.execute("create table if not exists proxytable (host text,     \
                                                          port text,      \
                                                          anony text,    \
                                                          protocol text, \
                                                          speed int)")
        self.conn.commit()

    def update(self, url):
        # 通过访问 http://www.example.com/ 确定是否正确工作
        inc_lock = threading.Lock()  # 数据递增用锁
        proxy_list = self.get_all()
        proxy_len = len(proxy_list)
        inc = [0]
        thread_num = 300
        if proxy_len < thread_num:
            thread_num = proxy_len
        threads = [None] * thread_num

        wait_time = [None] * proxy_len
        anony_type = [None] * proxy_len

        def check_proxy(proxy_list, wait_time, anony_type, inc):
            cur_num = -1
            cur_proxy = None
            while True:
                # print "{", inc[0], "}"
                #lock_time = time.time()
                with inc_lock:
                    if inc[0] >= proxy_len:
                        break
                    cur_num = inc[0]
                    inc[0] += 1
                # print time.time() - lock_time
                if cur_num % 200 == 0:
                    print "updated ", cur_num
                cur_proxy = proxy_list[cur_num]
                wait_time[cur_num], status_code, body = curl_get(
                    url, proxy=cur_proxy)
                anony_type[cur_num] = check_anony(cur_proxy)
                if status_code != 200:
                    wait_time[cur_num] = 1002
            # print "end", cur_num

        for i in xrange(thread_num):
            t = threading.Thread(
                target=check_proxy, args=([proxy_list, wait_time, anony_type, inc]))
            t.start()
            threads[i] = t
        for i in xrange(thread_num):
            threads[i].join()

        for i in xrange(proxy_len):
            c = self.conn.cursor()
            if wait_time[i]:
                update_str = "update proxytable set speed=" + \
                    str(wait_time[i]) + " where host='" + \
                    proxy_list[i]["host"] + "'"
                if anony_type[i]:
                    update_str = "update proxytable set speed=" + \
                        str(wait_time[i]) + ", anony='" + anony_type[i] + \
                        "' where host='" + proxy_list[i]["host"] + "'"
                c.execute(update_str)
        self.conn.commit()

    def __seq_to_dictlist(self, seq):
        # db sequnence to proxy dict
        # [(1,2,3), (4,5,6)] -> [{"a":1, "b":2, "c":3}, {...}]
        proxy_list = []
        for item in seq:
            proxy_dict = tuple_to_dict(item)
            proxy_list.append(proxy_dict)

        return proxy_list

    def __insert(self, proxy):

        # proxy = (x, x, x, x, x)
        if type([]) != type(proxy):
            proxy = [proxy]

        # 去重
        p_set = set([])
        for item in proxy:
            if item[0] not in p_set:
                p_set.add(item[0])
            else:
                proxy.remove(item)

        with db_lock:
            conn = sqlite3.connect(self.db)
            c = conn.cursor()
            proxy_len = len(proxy)
            del_items = [False] * proxy_len
            for i in xrange(proxy_len):
                item = proxy[i]
                host = item[0]
                select_str = "select * from proxytable where host = '" + \
                    host + "'"
                c.execute(select_str)
                if c.fetchone():
                    del_items[i] = True
            result_proxy = []
            for i in xrange(proxy_len):
                if del_items[i] == False:
                    result_proxy.append(proxy[i])
            try:
                c.executemany(
                    "INSERT INTO proxytable VALUES (?,?,?,?,?)", result_proxy)
            except:
                print "insert error while insert ", result_proxy
            conn.commit()

    def __get_proxy_by_func(self, func):
        # func is a function which get proxies from page
        # and return as [(x, x, x, x, x), ...] means (host, port, protocol,
        # anony, speed)

        proxy_list = func()
        try:
            self.__insert(proxy_list)
        except:
            print "result from %s error" % func.__name__

    def run_func_list(self):
        # 计划任务，间歇性执行
        for func in self.func_list:
            fetch_func = getattr(fetch, func, None)
            if fetch_func:
                t = threading.Thread(
                    target=self.__get_proxy_by_func, args=([fetch_func]))
                t.start()


def check_anony(proxy):
    _, x, body = curl_get("http://haha.pythonanywhere.com/realip", proxy)
    ips = re.findall(r"(?:\d+\.){3}\d+", body)

    if ips and ips[-1] == proxy["host"]:
        return "AP"
    return "UN"

if __name__ == "__main__":
    host = ProxyHost(True)
    ap = host.get_all()
    print len(ap)
    #from fetch_tools import find_ptotocol
    #for proxy in ap:
    #   print find_ptotocol(proxy["host"], proxy["port"])

    #proxy = ap[5]
    #_, x, body = curl_get("http://www.98bk.com/cycx/ip1/", proxy)
    # print body, "\n", x
