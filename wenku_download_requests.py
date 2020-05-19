# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/8

Todo: 使用requests下载百度文库文档

无法使文档变成已下载的状态

"""
import requests
from bs4 import BeautifulSoup
from urllib import parse

if __name__ == '__main__':
    payload = {
        'doc_id': 'aaf4ff0158eef8c75fbfc77da26925c52cc591e4',
        'downloadToken': 'f9641340a8ea428fa3c012306624fcf0',
        'ct': '20008',
        'storage': '1',
        'useTicket': '0',
        'target_uticket_num': '0',
        'sz': '33792',
        'v_code': '0',
        'v_input': '0',
        'req_vip_free_doc': '0',
    }
    # data = parse.urlencode(payload)
    # print(data)
    headers = {
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36',
        'Host': 'wenku.baidu.com',
        'Cookie': 'murmur=undefined--MacIntel; PSTM=1566033365; BIDUPSID=3B2FC32C0AFA1BBCBC36F232E644134A; wk_hotsearchword=ppt%E6%A8%A1%E7%89%88%26%E5%B0%8F%E5%AD%A6%E4%BD%9C%E6%96%87; _click_param_reader_query_ab=-1; _click_param_pc_rec_doc_2017_testid=4; BAIDUID=0C518A7A8BDECA5C68A4755CC8D4A092:FG=1; BDUSS=BxVDUtMnl3aGtRMDdLWHNkZ3Uzb1ZBbUhCTGxDcHJScDhBSEpjbUc4ZFJHTk5lRVFBQUFBJCQAAAAAAAAAAAEAAABHbiKcwda36DE1OAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFGLq15Ri6teTD; H_WISE_SIDS=141961_146257_142018_145118_145497_144989_144420_144134_145270_146308_145931_131862_131247_144682_137745_144250_141941_127969_146034_146551_145803_140593_142421_145703_145876_146000_131424_142207_146002_145597_107312_145380_146135_139909_146396_144966_142427_145607_140311_144762_144017_145397_143854_139914_110085; UM_distinctid=17203fe71a1a75-00ead5fe696533-30667d00-13c680-17203fe71a2c27; Hm_lvt_addc40d255fca71b9b06a07c2397b42a=1588300539,1588736705,1588892979,1589204906; murmur=undefined--MacIntel; isJiaoyuVip=1; userFirstTime=true; CNZZDATA1272960286=1229507467-1583494210-%7C1589764545; ZD_ENTRY=google; ___wk_scode_token=y8XOPT7P90jD1Zg10KUxk7BvfliZAO1rjUzgpEZbtu0%3D; Hm_lvt_d8bfb560f8d03bbefc9bdecafc4a4bf6=1588741410,1589730235,1589766997,1589768772; session_id=1589768772663; session_name=converter.baidu.com; Hm_lpvt_d8bfb560f8d03bbefc9bdecafc4a4bf6=1589768865',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cache-Control': 'no-cache',
        'Referer': 'https://wenku.baidu.com/view/aaf4ff0158eef8c75fbfc77da26925c52cc591e4.html?fr=search',
        'Sec-Fetch-Dest': 'iframe',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Origin': 'https://wenku.baidu.com',
        'Pragma': 'no-cache',
        'Upgrade-Insecure-Requests': '1',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
    }
    with requests.post('https://wenku.baidu.com/user/submit/download', headers=headers, data=payload) as r:
        print(r.status_code)
        print(r.headers)




