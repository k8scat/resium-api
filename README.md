# Resium

[![CodeFactor](https://www.codefactor.io/repository/github/resium-dev/resium/badge?s=203e0639dd031e8f239a574a23ea782c8ec73523)](https://www.codefactor.io/repository/github/resium-dev/resium)

基础镜像: https://git.ncucoder.com/hsowan/python37-django

OSS: https://oss.console.aliyun.com/bucket/oss-cn-hangzhou/ncucoder/overview

## Todo

* [x] 用户是否正在下载状态: 数据库 -> redis
    通过限制用户下载频率来达到用户
* [x] 集成稻壳模板
* [ ] 换绑手机号、邮箱
* [ ] tags 单独创建一个表
* [x] django-cors-headers 并没有返回 Access-Control-Allow-Origin
    use middleware to return Access-Control-Allow-Origin
* [ ] mq
* [ ] 重复保存资源的问题
* [x] 爬取CSDN已下载资源
* [x] 检查csdn当天下载数
* [ ] 后端分布式
* [ ] 删除 文件碎片
    * https://oss.console.aliyun.com/bucket/oss-cn-hangzhou/ncucoder/object
* [x] 集成知网
* [x] 上传奖励
* [ ] wenku_download_requests
* [x] nginx + gunicorn
    * https://www.zmrenwu.com/courses/hellodjango-blog-tutorial/materials/74/
    静态文件映射到本地
* [ ] TestCase
    * https://www.zmrenwu.com/courses/hellodjango-blog-tutorial/materials/87/
* [ ] Coverage.py 统计测试覆盖率
    * https://www.zmrenwu.com/courses/hellodjango-blog-tutorial/materials/89/
* [ ] parse_resource 和 download 重复解析资源信息的问题
* [ ] 后端接口地址更新的问题
    后端settings/prod.py
    前端.env.production
    微信公众号 > 基本配置 > 服务器配置 > 服务器地址
* [x] CSDN VIP文章
    https://blog.csdn.net/yangtao5202/article/details/82228857
* [ ] 开放API
* [ ] Use sha512 over md5 to verify file integrity
* [ ] 下载和保存上传资源是分开的
* [ ] 毕设、大作业代做
* [ ] 错误信息：{'code': 400, 'message': '资源不存在', 'data': ''}
    https://download.csdn.net/download/x_uhen/12013989
* [x] csdn自动上传，使用新账号
* [x] 机器人下载
* [ ] 知网下载补充
    https://kns.cnki.net/KCMS/detail/detail.aspx?dbcode=CMFD&dbname=CMFD2008&filename=2008138848.nh&v=MDAzNDdmWk9SckZ5RGtVcnpCVjEyN0ZySzdGdG5JcDVFYlBJUjhlWDFMdXhZUzdEaDFUM3FUcldNMUZyQ1VSN3E=
* [x] 短链接
* [x] 800m资源下载失败
* [x] 分离coolq
* [ ] 日志系统 elk
* [ ] 代码重构，资源下载的代码多处存在重复
* [ ] 800m资源下载成功后，check失败
* [ ] 语音验证码
* [ ] qq 登录
    https://connect.qq.com/manage.html#/appinfo/web/101864025
* [ ] 微云
    https://open.weiyun.com/api/twoa_restful_api.html
* [ ] 百度文库pdf解析
* [ ] 会员账号自主接入，提现
* [ ] 源自下载小程序
    https://git.cloudevops.cn/hsowan/resium-app
* [ ] 淘宝文库账号接入
    post http://doc110.com/login.php data {account: "6599362515", password: "9027855"}
    
    post http://doc110.com/post.php data {docUrl: "https://wenku.baidu.com/view/62c5485ed1d233d4b14e852458fb770bf68a3b76.html?from=search"}
    return {code: 200, downUrl: "url", times: "746", session: "8671203093", msg: "下载成功!", filename: "租房.doc", path: ""}
    
    get http://doc110.com/get.php return return {code: 200, gold: "746", withdraw: "2", withdraw_accept: true}
* [ ] 管理员上传资源，通过qq分享到群里
* [ ] 废弃手机绑定
* [ ] https://converter.baidu.com/?origin=wenkuConverterOther
* [ ] 限定分页数，不将所有的资源都暴露出来，比如只能展示30页
* [ ] 公众号添加百度文库VIP免费文档下载功能
* [ ] 第三方登录必然是相当于新账号注册，所以需要添加账号注销（也就是添加字段is_delete），以及已注册账号关联第三方账号
* [ ] github gitee第三方登录
* [ ] 前后端同时需要添加正则匹配的问题，考虑仅在后端进行判断

## CoolQ

https://github.com/richardchien/coolq-http-api

为 酷Q 提供通过 HTTP 或 WebSocket 接收事件和调用 API 的能力 https://cqhttp.cc/docs/

## 广告接入

* [阿里云云大使](https://promotion.aliyun.com/ntms/yunparter/personal-center.html#/)
* [腾讯云推广](https://console.cloud.tencent.com/spread/result)

## 部署流程

## 资源网站

* [百度文库VIP](https://wenku.baidu.com/ndvipmember/browse/vipprivilege)

## 资源代下网站

* [千文库](http://a.1000wk.com/)
* [免积分](http://www.itziy.com/)
* [QCSDN](http://qcsdn.com/)

* http://www.dcsdn.com/
* http://www.catalina.com.cn/

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