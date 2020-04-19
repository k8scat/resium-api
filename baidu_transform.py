# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/4/19

https://converter.baidu.com/?origin=wenkuConverterOther

PUT https://bj.bcebos.com/v1/pdf365-test/share/c779a2c5b0ae2c2e60fc3019cf7f3e312.pdf
HEADERS = {
    'authorization': 'bce-auth-v1/c7bbcddb820611eaafd201d9b2bc25ce/2020-04-19T06:27:26Z/1800/content-length;content-type;host;x-bce-date;x-bce-security-token/e44b95d123b4602306cc36436d0c148e7ddd876254c8bf22c96e5f524c5805a2',
    'content-type': 'application/pdf',
    'Host': 'bj.bcebos.com',
    'Origin': 'https://converter.baidu.com',
    'Referer': 'https://converter.baidu.com/detail?type=1&origin=wenkuConverterOther',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36',
    'x-bce-date': '2020-04-19T06:27:26Z',
    'x-bce-security-token': 'ZjkyZmQ2YmQxZTQ3NDcyNjk0ZTg1ZjYyYjlkZjNjODB8AAAAAJICAADEY9mDj8hGBLfTpma049i8fi4b7bH/0cJnTtSzF3aP9yFSCBcnO6iEw7o/+ma7ajtztQf1uvWoaSMrXwuAoZ3fAnW+KkS9wdVl55zkHYVmupk8V7nKz2c1dB+mnAimqFU5BTLWt1pZaU55ReyMCZB1sfqH9SEJLQZR2Uvw3/dHasAsfxFBJ/XiqRUYu+oRPAcgJFTKrKSW22y/LNoHxH4l7rE7eNEVSMrxsdvAAjCdIR/HvGKiSBmXq8/17iyFSBQT0fvo49+Zt7gzYo8laPvPRStSIr5QHP8u3sr5mftnUiFqdmla9S4G2udW/BUkP/fUQVdJOgvqOz0B/HIRh1OfnwGi6iN10kqji6MLhQm4jsZkhiorzvzCmmVxxmYinm3V4D6A+lfDT1jV3LOo0VrDN0oyw3M4D8fdNpFdexWy7JaA0jegK9G1Q5wjwj3yYa6VmTi/4AdCnC3/41AfNvYvXDvD2UjRc3zSidlX3d2df9TSfSmfSM1SXZ99cAL1HFQ='
}
x-bce-security-token: sessiontoken

POST https://converter.baidu.com/api/uploadfile
HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Cookie': 'PSTM=1566033365; BIDUPSID=3B2FC32C0AFA1BBCBC36F232E644134A; H_WISE_SIDS=144367_142529_142621_142019_144884_139047_141744_144990_144420_144135_144471_144482_136861_131862_144962_131246_144682_137746_144742_138883_140259_141941_127969_140066_144791_144339_140593_144250_144726_143922_144484_131423_144882_132547_145317_107317_145296_139908_144872_139884_143478_144966_142426_140312_142508_145397_143856_110085; UM_distinctid=17181a33b2811e-05c3a0bf33b4e7-396f7506-13c680-17181a33b31a8; cflag=13%3A3; jshunter-uuid=f11603d7-3e2c-442e-a8aa-c6e931069bff; BDUSS=xKWmxGeC1LNjNaakR5dkdBNURFRHAzQUZtcVpVdVZVNThvdG1qMVVhNkdvc0JlSVFBQUFBJCQAAAAAAAAAAAEAAABHbiKcwda36DE1OAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIYVmV6GFZleUm; session_id=1587194974191; session_name=; H_PS_PSSID=1458_21106_31341_30910_31270_30824_31086_31164_31195; Hm_lvt_addc40d255fca71b9b06a07c2397b42a=1586127958,1586498855,1586589958,1587209656; Hm_lpvt_addc40d255fca71b9b06a07c2397b42a=1587209656; BAIDUID=E91D2FB6DAE017C53B56F9117D947F99:FG=1; Hm_lvt_5c92be27af9d550bd3c0682f82b1ae8e=1586921827,1587277578; CNZZDATA1272960286=846215749-1584585228-https%253A%252F%252Fwenku.baidu.com%252F%7C1587276501; Hm_lpvt_5c92be27af9d550bd3c0682f82b1ae8e=1587277623',
    'Host': 'converter.baidu.com',
    'Origin': 'https://converter.baidu.com',
    'Referer': 'https://converter.baidu.com/detail?type=1&origin=wenkuConverterOther',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36'
}
FORM_DATA = {
    'url': 'http%3A%2F%2Fbj.bcebos.com%2Fpdf365-test%2Fshare%2Fc779a2c5b0ae2c2e60fc3019cf7f3e312.pdf',
    'file_name': 'c779a2c5b0ae2c2e60fc3019cf7f3e312.pdf',
    'size': 489383,
    'type': 1,
    'file_type': 'pdf',
    'request_channel': 2
}

POST https://converter.baidu.com/api/converterjob
HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Cookie': 'PSTM=1566033365; BIDUPSID=3B2FC32C0AFA1BBCBC36F232E644134A; H_WISE_SIDS=144367_142529_142621_142019_144884_139047_141744_144990_144420_144135_144471_144482_136861_131862_144962_131246_144682_137746_144742_138883_140259_141941_127969_140066_144791_144339_140593_144250_144726_143922_144484_131423_144882_132547_145317_107317_145296_139908_144872_139884_143478_144966_142426_140312_142508_145397_143856_110085; UM_distinctid=17181a33b2811e-05c3a0bf33b4e7-396f7506-13c680-17181a33b31a8; cflag=13%3A3; jshunter-uuid=f11603d7-3e2c-442e-a8aa-c6e931069bff; BDUSS=xKWmxGeC1LNjNaakR5dkdBNURFRHAzQUZtcVpVdVZVNThvdG1qMVVhNkdvc0JlSVFBQUFBJCQAAAAAAAAAAAEAAABHbiKcwda36DE1OAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIYVmV6GFZleUm; session_id=1587194974191; session_name=; H_PS_PSSID=1458_21106_31341_30910_31270_30824_31086_31164_31195; Hm_lvt_addc40d255fca71b9b06a07c2397b42a=1586127958,1586498855,1586589958,1587209656; Hm_lpvt_addc40d255fca71b9b06a07c2397b42a=1587209656; BAIDUID=E91D2FB6DAE017C53B56F9117D947F99:FG=1; Hm_lvt_5c92be27af9d550bd3c0682f82b1ae8e=1586921827,1587277578; CNZZDATA1272960286=846215749-1584585228-https%253A%252F%252Fwenku.baidu.com%252F%7C1587276501; Hm_lpvt_5c92be27af9d550bd3c0682f82b1ae8e=1587277623',
    'Host': 'converter.baidu.com',
    'Origin': 'https://converter.baidu.com',
    'Referer': 'https://converter.baidu.com/detail?type=1&origin=wenkuConverterOther',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36'
}
FORM_DATA = {
    'id': '311e52eef8c75fbfc77db207',
    'type': 1
}
RESPONSE = [
    {
        'status': {
            'code': 0,
            'msg': null
        },
        'data': []
    }
]

GET https://converter.baidu.com/api/converterjobdown?id=311e52eef8c75fbfc77db207


"""

import os
import django
from selenium.common.exceptions import TimeoutException

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resium.settings.prod')
django.setup()

import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from time import sleep
import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from downloader.models import BaiduAccount
import requests
from downloader.utils import get_random_ua


class BaiduTransformer:
    def __init__(self, filepath):
        self.filepath = filepath
        self.session_token = None
        self.access_key_id = None
        self.baidu_account = BaiduAccount.objects.get(is_enabled=True)

    def get_token(self):
        """
        x-bce-security-token: sessiontoken

        :return:
        """

        headers = {
            'user-agent': get_random_ua()
        }
        with requests.get('https://converter.baidu.com/detail?type=1&origin=wenkuConverterOther', headers=headers) as r:
            if r.status_code == requests.codes.OK:
                soup = BeautifulSoup(r.text, 'lxml')
                auth = soup.select('div.sd-container-section')[0]
                self.session_token = auth.get('sessiontoken', None)
                self.access_key_id = auth.get('accesskeyid', None)

    def pdf2word(self):
        """
        bce-auth-v1/e0f89413821611ea9a8f2fbf511f1c10/2020-04-19T08:28:22Z/1800/content-length;content-type;host;x-bce-date;x-bce-security-token/5967d95604362a7d77155459ee40df94b9c5a82f305f3f6cb9f84bdd7d40c297

        :return:
        """
        date = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        authorization = f'bce-auth-v1/{self.access_key_id}/{date}/1800/content-length;content-type;host;x-bce-date;x-bce-security-token/'

        headers = {
            'authorization': 'bce-auth-v1/c7bbcddb820611eaafd201d9b2bc25ce/2020-04-19T06:27:26Z/1800/content-length;content-type;host;x-bce-date;x-bce-security-token/e44b95d123b4602306cc36436d0c148e7ddd876254c8bf22c96e5f524c5805a2',
            'content-type': 'application/pdf',
            'Host': 'bj.bcebos.com',
            'Origin': 'https://converter.baidu.com',
            'Referer': 'https://converter.baidu.com/detail?type=1&origin=wenkuConverterOther',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36',
            'x-bce-date': '2020-04-19T06:27:26Z',
            'x-bce-security-token': 'ZjkyZmQ2YmQxZTQ3NDcyNjk0ZTg1ZjYyYjlkZjNjODB8AAAAAJICAADEY9mDj8hGBLfTpma049i8fi4b7bH/0cJnTtSzF3aP9yFSCBcnO6iEw7o/+ma7ajtztQf1uvWoaSMrXwuAoZ3fAnW+KkS9wdVl55zkHYVmupk8V7nKz2c1dB+mnAimqFU5BTLWt1pZaU55ReyMCZB1sfqH9SEJLQZR2Uvw3/dHasAsfxFBJ/XiqRUYu+oRPAcgJFTKrKSW22y/LNoHxH4l7rE7eNEVSMrxsdvAAjCdIR/HvGKiSBmXq8/17iyFSBQT0fvo49+Zt7gzYo8laPvPRStSIr5QHP8u3sr5mftnUiFqdmla9S4G2udW/BUkP/fUQVdJOgvqOz0B/HIRh1OfnwGi6iN10kqji6MLhQm4jsZkhiorzvzCmmVxxmYinm3V4D6A+lfDT1jV3LOo0VrDN0oyw3M4D8fdNpFdexWy7JaA0jegK9G1Q5wjwj3yYa6VmTi/4AdCnC3/41AfNvYvXDvD2UjRc3zSidlX3d2df9TSfSmfSM1SXZ99cAL1HFQ='
        }


def transform(filepath):
    headers = {
        'cookie': 'PSTM=1566033365; BIDUPSID=3B2FC32C0AFA1BBCBC36F232E644134A; H_WISE_SIDS=144367_142529_142621_142019_144884_139047_141744_144990_144420_144135_144471_144482_136861_131862_144962_131246_144682_137746_144742_138883_140259_141941_127969_140066_144791_144339_140593_144250_144726_143922_144484_131423_144882_132547_145317_107317_145296_139908_144872_139884_143478_144966_142426_140312_142508_145397_143856_110085; UM_distinctid=17181a33b2811e-05c3a0bf33b4e7-396f7506-13c680-17181a33b31a8; cflag=13%3A3; jshunter-uuid=f11603d7-3e2c-442e-a8aa-c6e931069bff; BDUSS=xKWmxGeC1LNjNaakR5dkdBNURFRHAzQUZtcVpVdVZVNThvdG1qMVVhNkdvc0JlSVFBQUFBJCQAAAAAAAAAAAEAAABHbiKcwda36DE1OAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIYVmV6GFZleUm; session_id=1587194974191; session_name=; H_PS_PSSID=1458_21106_31341_30910_31270_30824_31086_31164_31195; Hm_lvt_addc40d255fca71b9b06a07c2397b42a=1586127958,1586498855,1586589958,1587209656; Hm_lpvt_addc40d255fca71b9b06a07c2397b42a=1587209656; BAIDUID=E91D2FB6DAE017C53B56F9117D947F99:FG=1; Hm_lvt_5c92be27af9d550bd3c0682f82b1ae8e=1586921827,1587277578; Hm_lpvt_5c92be27af9d550bd3c0682f82b1ae8e=1587277623; CNZZDATA1272960286=846215749-1584585228-https%253A%252F%252Fwenku.baidu.com%252F%7C1587281901',
        'user-agent': get_random_ua()
    }
    with requests.get('https://converter.baidu.com/detail?type=1&origin=wenkuConverterOther', headers=headers) as r:
        if r.status_code == requests.codes.OK:
            soup = BeautifulSoup(r.text, 'lxml')
            x_bce_security_token = soup.select('div.sd-container div.sd-container-section')[0].get('sessiontoken', None)

    filename = filepath.split(os.path.sep)[-1]
    with requests.put(f'https://bj.bcebos.com/v1/pdf365-test/share/c779a2c5b0ae2c2e60fc3019cf7f3e312.pdf') as r:
        pass


if __name__ == '__main__':
    driver = webdriver.Chrome()
    try:
        driver.get('https://converter.baidu.com/detail?type=1&origin=wenkuConverterOther')
        baidu_account = BaiduAccount.objects.get(is_enabled=True)
        cookies = json.loads(baidu_account.cookies)
        for cookie in cookies:
            if 'expiry' in cookie:
                del cookie['expiry']
            driver.add_cookie(cookie)
        driver.get('https://converter.baidu.com/detail?type=1&origin=wenkuConverterOther')
        sleep(3)
        upload_input = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.ID, 'upload_file'))
        )
        upload_input.send_keys('/Users/mac/Downloads/c779a2c5b0ae2c2e60fc3019cf7f3e31(2).pdf')
        try:
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.XPATH, "//p[@class='converterNameV']"))
            )
            download_url = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.XPATH, "//a[@class='dwon-document']"))
            ).get_attribute('href')
            print(download_url)
        except TimeoutException:
            print('转换失败')

        sleep(100)

    finally:
        driver.close()
