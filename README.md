# Resium API

## Todo

- [ ] Dev环境
- [ ] 网站优化
- [x] [模板之家下载](http://www.cssmoban.com/)
- [x] 用户是否正在下载状态: 数据库 -> redis
  - [x] 通过限制用户下载频率来达到用户
- [x] 集成稻壳模板
- [ ] tags 单独创建一个表
- [x] django-cors-headers 并没有返回 Access-Control-Allow-Origin
  - [x] use middleware to return Access-Control-Allow-Origin
- [ ] mq
- [ ] 重复保存资源的问题
- [x] 爬取CSDN已下载资源
- [x] 检查csdn当天下载数
- [ ] 后端分布式/集群
  - [ ] go实现集群部署
- [ ] [OSS 删除文件碎片](https://oss.console.aliyun.com/bucket/oss-cn-hangzhou/ncucoder/object)
- [x] 集成知网
- [x] wenku_download_requests使用requests下载百度文库
  - [DownHub](https://hsowan.coding.net/p/resium/d/DownHub/git)
- [x] [nginx + gunicorn](https://www.zmrenwu.com/courses/hellodjango-blog-tutorial/materials/74/)
  - [ ] 静态文件映射到本地
- [ ] [TestCase](https://www.zmrenwu.com/courses/hellodjango-blog-tutorial/materials/87/)
- [ ] [Coverage.py 统计测试覆盖率](https://www.zmrenwu.com/courses/hellodjango-blog-tutorial/materials/89/)
- [ ] parse_resource 和 download 重复解析资源信息的问题
- [ ] 后端接口地址更新的问题（更换域名）
  - 后端 settings/prod.py
  - 前端 .env.production
  - 微信公众号 > 基本配置 > 服务器配置 > 服务器地址
- [x] [CSDN VIP文章](https://blog.csdn.net/yangtao5202/article/details/82228857)
- [ ] Use sha512 over md5 to verify file integrity
- [ ] 下载和保存上传资源是分开的
- [ ] [错误信息：{'code': 400, 'message': '资源不存在', 'data': ''}](https://download.csdn.net/download/x_uhen/12013989)
- [x] ~~csdn自动上传，使用新账号（会导致封号）~~
- [x] 机器人下载
- [ ] [知网下载补充](https://kns.cnki.net/KCMS/detail/detail.aspx?dbcode=CMFD&dbname=CMFD2008&filename=2008138848.nh&v=MDAzNDdmWk9SckZ5RGtVcnpCVjEyN0ZySzdGdG5JcDVFYlBJUjhlWDFMdXhZUzdEaDFUM3FUcldNMUZyQ1VSN3E=)
- [x] 短链接
- [x] 800m资源下载失败
- [x] 分离coolq
- [ ] 日志系统 elk
- [ ] 代码重构，资源下载的代码多处存在重复
- [x] 800m资源下载成功后，aliyun oss check失败
    解决方案：不check上传资源的完整性，默认上传OK
- [x] 语音验证码，结合qq机器人可以实现
- [ ] [微云](https://open.weiyun.com/api/twoa_restful_api.html)
- [ ] [百度文库pdf解析，类似于冰点文库](http://www.html22.com/doc/)
- [x] 会员账号自主接入
  - [ ] 微信自动提现
- [x] [源自下载小程序](https://github.com/k8scat/resium-app)
- [x] [百度文档格式转换](https://converter.baidu.com/?origin=wenkuConverterOther)
- [x] 限定分页数，不将所有的资源都暴露出来，比如只能展示30页
    采用滚动加载
- [x] gitee第三方登录
- [ ] 前后端同时需要添加正则匹配的问题，考虑仅在后端进行判断
- [ ] 命令行工具 py
    例如: rd -resource url 就可以下载资源
- [ ] 快速切换到更新服务器
- [ ] session保存用户信息的问题
- [x] 302重定向或者303see other 设置cookies会丢失
    解决方案：添加cookie时设置domain
- [x] dingtalk + sentry
  - [ ] 解决方案：sentry + slack
- [ ] [百度网盘开发平台](https://pan.baidu.com/union)
- [ ] 数据库集群
- [ ] OAuth
  - [ ] OpenSource
    - [ ] [JustAuth](https://gitee.com/yadong.zhang/JustAuth?_from=gitee_search)
  - [ ] Platforms
    - [x] [QQ](https://connect.qq.com/manage.html#/appinfo/web/101864025)
    - [x] GitHub
    - [x] [Gitee](https://gitee.com/oauth/applications/3833)
    - [x] [OSC](https://www.oschina.net/openapi/client)
    - [ ] [renren](http://app.renren.com/developers/newapp/600758/main)
    - [ ] [sina](https://open.weibo.com/developers/identity)
    - [x] [baidu](http://developer.baidu.com/console#app/19467092)
    - [ ] [dingtalk](https://ding-doc.dingtalk.com/doc#/serverapi2/kymkv6)
    - [x] [Coding](https://help.coding.net/docs/project/open/oauth.html)
    - [x] Teambition
    - [修改图片大小的工具](https://www.sojson.com/image/change.html)
- [x] 下载失败清除用户redis uid
- [ ] [Django 时间、时区的问题](https://www.jianshu.com/p/c1dee7d3cbb9)

```python
DwzRecord.objects.filter(user=user, create_time__day=timezone.now().day).count()
    
timezone.now() UTC
timezone.datetime.now() UTC+8
```

- [x] csdn账号当天下载量到达时，尝试自动切换
- [x] 积分使用记录表
- [x] uid 改成6位数字
