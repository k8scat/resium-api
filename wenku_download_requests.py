# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/8

Todo: 使用requests下载百度文库文档

"""
import requests
from bs4 import BeautifulSoup
from urllib import parse

if __name__ == '__main__':
    resource_url = 'https://wenku.baidu.com/view/6b03c29ea417866fb94a8e1f.html?from=search'
    doc_id = resource_url.split('wenku.baidu.com/view/')[1].split('.')[0]
    print(doc_id)

    create_download_file_url = 'https://wenku.baidu.com/user/submit/createdownloadfile'
    headers = {
        'referer': f'https://wenku.baidu.com/browse/downloadrec?doc_id={doc_id}&wp=2&',
        'cookie': 'BAIDUID=DC04FEAF2DBD3D931E7DBB54235D72C6:FG=1; PSTM=1566033365; BIDUPSID=3B2FC32C0AFA1BBCBC36F232E644134A; _click_param_pc_rec_doc_2017_testid=5; wk_hotsearchword=ppt%E6%A8%A1%E7%89%88%26%E5%B0%8F%E5%AD%A6%E4%BD%9C%E6%96%87; _ga=GA1.2.136641008.1583403161; __xsptplus861=861.1.1583403193.1583403193.1%234%7C%7C%7C%7C%7C%23%2340gEX34KiE4LhWJVMEaFzgQy8FDBXGcU%23; UM_distinctid=170af13270625-0dd5e96d968422-396d7406-13c680-170af1327079fe; cflag=13%3A3; BDUSS=Y0dzhLOUtJalJvUmVla21IMmFmMTFESlh3dEZuc2xUREdwYXdmLVZ0MmdVcE5lRVFBQUFBJCQAAAAAAAAAAAEAAABHbiKcwda36DE1OAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAKDFa16gxWteMW; Hm_lvt_addc40d255fca71b9b06a07c2397b42a=1583563720,1583727762,1583942594,1584433762; Hm_lvt_d8bfb560f8d03bbefc9bdecafc4a4bf6=1584352593,1584591365,1584640621,1584642914; session_name=; murmur=87b19902247ce06ba29bf64e5e153bb3; isJiaoyuVip=1; ZD_ENTRY=google; session_id=1584699446206; CNZZDATA1272960286=1229507467-1583494210-%7C1584698688; ___wk_scode_token=84Pm2xnw0ICFSf36h5iiKsezA2O8YiuQ69%2Fk%2BNASQ30%3D; Hm_lpvt_d8bfb560f8d03bbefc9bdecafc4a4bf6=1584699913',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'
    }
    payload = f'doc_id={doc_id}'
    with requests.post(create_download_file_url, headers=headers, data=payload) as r:
        if r.status_code == requests.codes.OK and r.json()['status']['code'] == 0:
            print(r.json())

            headers = {
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
                'cookie': 'BAIDUID=DC04FEAF2DBD3D931E7DBB54235D72C6:FG=1; PSTM=1566033365; BIDUPSID=3B2FC32C0AFA1BBCBC36F232E644134A; _click_param_pc_rec_doc_2017_testid=5; wk_hotsearchword=ppt%E6%A8%A1%E7%89%88%26%E5%B0%8F%E5%AD%A6%E4%BD%9C%E6%96%87; _ga=GA1.2.136641008.1583403161; __xsptplus861=861.1.1583403193.1583403193.1%234%7C%7C%7C%7C%7C%23%2340gEX34KiE4LhWJVMEaFzgQy8FDBXGcU%23; UM_distinctid=170af13270625-0dd5e96d968422-396d7406-13c680-170af1327079fe; cflag=13%3A3; BDUSS=Y0dzhLOUtJalJvUmVla21IMmFmMTFESlh3dEZuc2xUREdwYXdmLVZ0MmdVcE5lRVFBQUFBJCQAAAAAAAAAAAEAAABHbiKcwda36DE1OAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAKDFa16gxWteMW; Hm_lvt_addc40d255fca71b9b06a07c2397b42a=1583563720,1583727762,1583942594,1584433762; Hm_lvt_d8bfb560f8d03bbefc9bdecafc4a4bf6=1584352593,1584591365,1584640621,1584642914; session_name=; murmur=87b19902247ce06ba29bf64e5e153bb3; isJiaoyuVip=1; ZD_ENTRY=google; session_id=1584699446206; CNZZDATA1272960286=1229507467-1583494210-%7C1584698688; ___wk_scode_token=84Pm2xnw0ICFSf36h5iiKsezA2O8YiuQ69%2Fk%2BNASQ30%3D; Hm_lpvt_d8bfb560f8d03bbefc9bdecafc4a4bf6=1584699913',
                'referer': resource_url
            }
            with requests.get(resource_url, headers=headers) as r_:
                soup = BeautifulSoup(r_.text, 'lxml')
                download_token = soup.find('input', attrs={'name': 'downloadToken'})['value']
                payload = {
                    'doc_id': doc_id,
                    'downloadToken': download_token
                }
                print(payload)
                headers.setdefault('content-type', 'multipart/form-data')
                print(headers)
                with requests.post('https://wenku.baidu.com/user/submit/download', headers=headers, data=payload, stream=True) as _:
                    print(_.status_code)
                    print(r.content)
                    if _.status_code == requests.codes.OK:
                        print(_.headers)
                        filename = _.headers['Content-Disposition'].split('"')[1]



