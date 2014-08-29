# -*- coding: utf-8 -*-

"""
    本文件为抓取代理的函数所在页面。抓取函数名统一为 fetch_xxx 格式，并
    在函数注释里标明抓取的url或网站。
    函数要求返回一个list，每个list元素为一个长度为5的tuple组成。
    每个tuple的每一个字段都要求按照规范填充，如下：

    example:return  [("123.77.9.44", "8080", "socks4", "DP", "3"),
                     ("123.44.2.44", "8077", "https", UN", "1001"), ...]

    规范：IP, PORT 为十进制数组成
          匿名性为 [DP|AP|TP|HAP|UN] 之一，区分大小写
          协议为   [socks4|socks5|http|https] 区分大小写，统一大写
    
    要求 fetch_xxx 函数完成格式化数据的工作（或者调用filter_fatch,但该函
    数可能会丢弃大量不规范的数据）

    可以使用 test_func_return 来测试函数返回结果是否符合要求:

                test_func_return(fetch_xxx)

"""

from fetch_tools import filter_fetch, test_func_return, curl_get, find_ptotocol

import threading
import requests
import re
from bs4 import BeautifulSoup as bs


def fetch_letushide():
    """http://letushide.com/"""

    #print "start fetch_letushide"
    proxy_list = []

    start_soup = bs(requests.get("http://letushide.com/").text)
    num = int(start_soup.find(id="page").find_all("a")[-1].string)

    def soup_to_proxies(soup):
        plist = []
        trs = soup.find_all("tr", id="data")
        for tr in trs:
            tds = tr.find_all("td")
            items = map(lambda x: x.string, tds)
            proxy = [items[x] for x in [1, 2, 3, 4, 5]]
            plist.append(proxy)
        return plist

    def url_to_proxies(url, results, i):
        soup = bs(requests.get(url).text)
        results[i] = soup_to_proxies(soup)

    threads = [None] * (num - 1)
    results = [None] * (num - 1)

    for i in range(len(threads)):
        url = "http://letushide.com/" + \
            str(i + 2) + "/list_of_free_proxy_servers"
        threads[i] = threading.Thread(
            target=url_to_proxies, args=([url, results, i]))
        threads[i].start()
    for i in range(len(threads)):
        threads[i].join()

    proxy_list += soup_to_proxies(start_soup)
    for i in range(len(threads)):
        proxy_list += results[i]

    return filter_fetch(proxy_list)


def fetch_proxies_org():
    """http://proxies.org/2014/05/"""

    proxy_list = []

    def url_to_proxies(url, results, i):
        plist = []
        data = requests.get(url).text
        items = re.findall(r"(?:\d+\.){3}\d+:\d+", data)
        if not items:
            return False
        for item in items:
            part = item.split(":")
            protocol = find_ptotocol(part[0], part[1])
            plist.append((part[0], part[1], protocol, "UN", "1001"))
        results[i] = plist

    threads = [None] * 7
    results = [None] * 7
    for i in range(7):
        url = "http://proxies.org/2014/0%s/" % (i+2)
        threads[i] = threading.Thread(
            target=url_to_proxies, args=([url, results, i]))
        threads[i].start()
    for i in range(7):
        threads[i].join()

    for i in range(7):
        #print i
        #print results[i]
        proxy_list += results[i]

    #去重
    p_set = set([])
    for item in proxy_list:
        if item[0] not in p_set:
            p_set.add(item[0])
        else:
            proxy_list.remove(item)

    #print "proxies org len:", len(proxy_list)
    return filter_fetch(proxy_list)


if __name__ == "__main__":
    test_func_return(fetch_proxies_org)
