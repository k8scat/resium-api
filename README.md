# Resium

[![构建状态](https://hsowan.coding.net/badges/resium/job/274286/build.svg)](https://hsowan.coding.net/p/resium/ci/job)

基础镜像: https://code.aliyun.com/hsowan/python37-django/tree/master

OSS: https://oss.console.aliyun.com/bucket/oss-cn-hangzhou/ncucoder/overview

## 扫码登录流程

前端生成一张二维码，就是一个url 含有唯一标志

请求后端接口保存二维码的唯一标志、过期时间以及状态

前端带上唯一标志轮询后端接口，判断该二维码的状态是否改变

如果改变，则表示已登录

用户使用小程序进行扫码，带上用户信息、二维码唯一标志

## Todo

* [ ] 网站优化
* [x] 模板之家下载
    http://www.cssmoban.com/
* [x] 用户是否正在下载状态: 数据库 -> redis
    通过限制用户下载频率来达到用户
* [x] 集成稻壳模板
* [ ] tags 单独创建一个表
* [x] django-cors-headers 并没有返回 Access-Control-Allow-Origin
    use middleware to return Access-Control-Allow-Origin
* [ ] mq
* [ ] 重复保存资源的问题
* [x] 爬取CSDN已下载资源
* [x] 检查csdn当天下载数
* [ ] 后端分布式/集群
    * [ ] go实现集群部署
* [ ] 删除 文件碎片
    * https://oss.console.aliyun.com/bucket/oss-cn-hangzhou/ncucoder/object
* [x] 集成知网
* [x] wenku_download_requests使用requests下载百度文库
    * [DownHub](https://hsowan.coding.net/p/resium/d/DownHub/git)
* [x] nginx + gunicorn
    * https://www.zmrenwu.com/courses/hellodjango-blog-tutorial/materials/74/
    静态文件映射到本地
* [ ] TestCase
    * https://www.zmrenwu.com/courses/hellodjango-blog-tutorial/materials/87/
* [ ] Coverage.py 统计测试覆盖率
    * https://www.zmrenwu.com/courses/hellodjango-blog-tutorial/materials/89/
* [ ] parse_resource 和 download 重复解析资源信息的问题
* [ ] 后端接口地址更新的问题（更换域名）
    后端settings/prod.py
    前端.env.production
    微信公众号 > 基本配置 > 服务器配置 > 服务器地址
* [x] CSDN VIP文章
    https://blog.csdn.net/yangtao5202/article/details/82228857
* [ ] Use sha512 over md5 to verify file integrity
* [ ] 下载和保存上传资源是分开的
* [ ] 错误信息：{'code': 400, 'message': '资源不存在', 'data': ''}
    https://download.csdn.net/download/x_uhen/12013989
* [x] ~~csdn自动上传，使用新账号（会导致封号）~~
* [x] 机器人下载
* [ ] 知网下载补充
    https://kns.cnki.net/KCMS/detail/detail.aspx?dbcode=CMFD&dbname=CMFD2008&filename=2008138848.nh&v=MDAzNDdmWk9SckZ5RGtVcnpCVjEyN0ZySzdGdG5JcDVFYlBJUjhlWDFMdXhZUzdEaDFUM3FUcldNMUZyQ1VSN3E=
* [x] 短链接
* [x] 800m资源下载失败
* [x] 分离coolq
* [ ] 日志系统 elk
* [ ] 代码重构，资源下载的代码多处存在重复
* [x] 800m资源下载成功后，aliyun oss check失败
    解决方案：不check上传资源的完整性，默认上传OK
* [x] 语音验证码，结合qq机器人可以实现
* [ ] 微云
    https://open.weiyun.com/api/twoa_restful_api.html
* [ ] 百度文库pdf解析，类似于冰点文库
    http://www.html22.com/doc/
* [x] 会员账号自主接入
    * [ ] 微信自动提现
* [x] 源自下载小程序
    https://git.cloudevops.cn/hsowan/resium-app
* [x] 百度文档格式转换
    https://converter.baidu.com/?origin=wenkuConverterOther
* [x] 限定分页数，不将所有的资源都暴露出来，比如只能展示30页
    采用滚动加载
* [x] gitee第三方登录
* [ ] 前后端同时需要添加正则匹配的问题，考虑仅在后端进行判断
* [ ] 命令行工具 py
    例如: rd -resource url 就可以下载资源
* [ ] 快速切换到更新服务器
* [ ] session保存用户信息的问题
* [x] 302重定向或者303see other 设置cookies会丢失
    解决方案：添加cookie时设置domain
* [x] dingtalk + sentry
    解决方案：sentry + slack
* [ ] 百度网盘开发平台
    https://pan.baidu.com/union
* [ ] 数据库集群
* [ ] OAuth
    https://gitee.com/yadong.zhang/JustAuth?_from=gitee_search

    * [x] QQ https://connect.qq.com/manage.html#/appinfo/web/101864025
        * [ ] 或许可以优化
    * [x] GitHub
    * [x] Gitee https://gitee.com/oauth/applications/3833
    * [x] OSC https://www.oschina.net/openapi/client
    * [ ] renren http://app.renren.com/developers/newapp/600758/main
    * [ ] sina https://open.weibo.com/developers/identity
    * [x] baidu http://developer.baidu.com/console#app/19467092
    * [ ] dingtalk https://ding-doc.dingtalk.com/doc#/serverapi2/kymkv6
        https://oapi.dingtalk.com/connect/qrconnect?appid=dingoawbeug9zmphewuplb&response_type=code&scope=snsapi_login&state=success&redirect_uri=https://api.resium.cn/oauth/dingtalk/
    * [x] Coding
        https://hsowan.coding.net/user/account/setting/applications/1376
        https://help.coding.net/docs/project/open/oauth.html
    * [x] Teambition
    
    修改图片大小的工具：https://www.sojson.com/image/change.html
* [x] 下载失败清除用户redis uid
* [ ] Django 时间、时区的问题
    DwzRecord.objects.filter(user=user, create_time__day=timezone.now().day).count()
    
    https://www.jianshu.com/p/c1dee7d3cbb9
    timezone.now() UTC
    timezone.datetime.now() UTC+8
* [x] csdn账号当天下载量到达时，尝试自动切换
* [x] 积分使用记录表
* [x] uid 改成6位数字

## 广告接入

* [阿里云云大使](https://promotion.aliyun.com/ntms/yunparter/personal-center.html#/)
* [腾讯云推广](https://console.cloud.tencent.com/spread/result)

## 资源网站

* [百度文库VIP](https://wenku.baidu.com/ndvipmember/browse/vipprivilege)

## 资源代下网站

* [千文库](http://a.1000wk.com/)
* [免积分](http://www.itziy.com/)
* [QCSDN](http://qcsdn.com/)

* [Catalina 1](http://www.dcsdn.com/)
* [Catalina 2](http://www.catalina.com.cn/)

* [脚本之家电子书下载](https://www.jb51.net/books/)

## Decorator

https://github.com/GrahamDumpleton/wrapt

## 阿里云OSS文档

https://help.aliyun.com/document_detail/85288.html?spm=a2c4g.11186623.6.826.71481695EDNlhM

## CSDN资源共享规范

https://download.csdn.net/help

## 百度文库协议

https://wenku.baidu.com/portal/browse/help#help/24

严禁用户以任何方式转让、出售自己的百度文库账号与积分，一经发现，百度有权立即封禁该账号；

## 百度文库解析

* [Python在线百度文库爬虫(免下载券)](https://www.jianshu.com/p/c8e10ec26342)

## Django template 复用

https://www.cnblogs.com/zealousness/p/8757144.html

## 飞书接入

* [机器人和消息会话事件](https://open.feishu.cn/document/ukTMukTMukTM/uMTNxYjLzUTM24yM1EjN)
* [发送文本消息](https://open.feishu.cn/document/ukTMukTMukTM/uUjNz4SN2MjL1YzM)