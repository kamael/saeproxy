# -*- coding: utf-8 -*-

"""
"""
import pycurl
import StringIO
import random
import time
import re
import threading

__all__ = ["filter_fetch", "test_func_return"]

protocols = ["socks4", "socks5", "http", "https"]
anony = ["DP", "AP", "TP", "HAP", "UN"]

def tuple_to_dict(tup):
    # (1,2,3)-> {"a":1, "b":2, "c":3}
    proxy_dict = {"host": tup[0],
                  "port": tup[1],
                  "protocol": tup[2],
                  "anony": tup[3],
                  "speed": tup[4]
                  }
    return proxy_dict

def frag_match(regex, fragment):
    match = re.match(regex, fragment)
    return match and match.group() == fragment

def match_IP(fragment):
    return fragment and frag_match(r"\d+\.\d+\.\d+\.\d+", fragment)

def match_number(fragment):
    return fragment and frag_match(r"\d+", fragment)

def match_protocal(fragment):
    return fragment and fragment in protocols

def match_anony(fragment):
    return fragment and fragment in anony

def filter_fetch(proxy_list):
    proxy_len = len(proxy_list)
    del_items = [False]*proxy_len

    for i in xrange(proxy_len):
        proxy = list(proxy_list[i])

        if not match_IP(proxy[0]):
            del_items[i] = True
            continue

        if not match_number(proxy[1]):
            del_items[i] = True
            continue

        if proxy[2]:
            proxy[2] = proxy[2].lower()
        if not match_protocal(proxy[2]):
            if proxy[2] == "sock4":
                proxy[2] = "socks4"
            if proxy[2] == "sock5":
                proxy[2] = "socks5"
        
        if proxy[3]:
            proxy[3] = proxy[3].lower()
        if not match_anony(proxy[3]):
            proxy[3] = "UN"

        if not proxy[4]:
            proxy[4] = "1001"

        try:
            proxy[4] = str(proxy[4])
        except:
            proxy[4] = "1001"

        #if proxy[4] != "1001":
        #    print "kkk", proxy[4], type(proxy[4])

        proxy_list[i] = tuple(proxy_list[i])

    result_list = []
    for i in xrange(proxy_len):
        if del_items[i] == False:
            result_list.append(proxy_list[i])
    return result_list


def test_func_return(func):
    """
    参数为抓取proxies的函数，写完函数调用一下这个test函数测试结果是否符合
    数据库要求，以防结果出错。
    (IP, PORT, Protocol, Anony, Time)
    """

    proxy_list = func()

    if not type(proxy_list) == type([]):
        print "returned is not a list"
    if not proxy_list or not proxy_list[0]:
        print "returned has no data"
    for proxy in proxy_list:
        if len(proxy) != 5:
            print "proxy tuple length error, it should be 5"
            break
        if not match_IP(proxy[0]):
            print proxy[0], "is not a valid IP"
            break
        if not match_number(proxy[1]):
            print proxy[1], "is not a valid PORT"
            break
        if not match_protocal(proxy[2]):
            print proxy[2], "is not a valid protocol, it should be one of [socks4|socks5|http|https]"
            break
        if not match_anony(proxy[3]):
            print proxy[3], "is not a valid anony field, it should be one of [DP|AP|TP|HAP|UN]"
            break
        if not match_number(proxy[4]):
            print proxy[4], "is not a valid time"
            break
    print "get", len(proxy_list), "work proxies"


#测试函数，使用curl
def curl_get(url, proxy=None, timeout=5):
    """
    url = "http://xxx.xxx"
    proxy = {
        "xxx": "xxx",
        ...
    }
    timeout = {{number}}
    """
    if not isinstance(proxy, dict):
        raise TypeError("proxy is not a dict")

    #t = time.time()
    curl = pycurl.Curl()
    buff = StringIO.StringIO()
    curl.setopt(pycurl.URL, url)
    curl.setopt(pycurl.WRITEFUNCTION, buff.write)
    curl.setopt(pycurl.TIMEOUT, timeout)
    
    curl.setopt(pycurl.HTTPHEADER, ['X-Forwarded-For: '+ips(),
                                    'User-Agent: Mozilla/5.0 (Windows NT 6.1) \
                                    AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.97 Safari/537.11'])
    if proxy:
        proxy_url = proxy["protocol"] + u"://" + \
            proxy["host"] + u":" + proxy["port"]
        #print proxy_url
        if proxy["protocol"] == "socks4":
            curl.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS4)
        elif proxy["protocol"] == "socks5":
            curl.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5)
        print proxy_url
        curl.setopt(pycurl.PROXY, proxy_url)
    t = time.time()
    try:
        curl.perform()
    except pycurl.error as e:
        # print "time out: ",e
        return 1002, 400, ""
    wait = time.time() - t
    status_code = curl.getinfo(pycurl.HTTP_CODE)
    body = buff.getvalue()
    # print "net:", time.time() - t
    return wait, status_code, body

#伪造ip
def feakip():
    l = []
    for i in range(4):
        num = str(random.randint(1,254))
        l.append(num)
    return ".".join(l)

#伪造ip链
def ips():
    l = []
    for x in range(random.randint(1,4)):
        l.append(feakip())
    l = ", ".join(l)
    return l

#查找代理服务器类型，socks4, socks5, http, https
def find_ptotocol(host, port):
    return "http"
    l = len(protocols)
    returns = [False] * l
    threads = [None] * l

    def get(proyocols, returns, i):
        url = "http://example.com"
        proxy = (host, port, proyocols[i], "UN", "1001")
        _, status_code, body = curl_get(url, proxy=tuple_to_dict(proxy))
        if status_code == 200:
            returns[i] = True

    for i in range(l):
        t = threading.Thread(target=get, args = ([protocols, returns, i]))
        threads[i] = t
        t.start()

    for i in range(l):
        threads[i].join()

    print returns
    for i in range(l):
        if returns[i] == True:
            return protocols[i]

    #todo hack 不可用就返回 http
    return "http" 

if __name__ == "__main__":
    pass