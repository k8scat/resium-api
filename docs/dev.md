# 开发文档

## 开发环境

- python3.7
  - virtualenv
- Docker
- MySQL 8
- Redis
- Selenium in Docker

> MySQL/ Redis/ Selenium 使用 resium-scripts/dev.yaml 进行启动

### MacOS

- [ ] brew install mysql

## [Decorator](https://github.com/GrahamDumpleton/wrapt)

## [阿里云 OSS 文档](https://help.aliyun.com/document_detail/85288.html?spm=a2c4g.11186623.6.826.71481695EDNlhM)

## 百度文库解析

- [Python在线百度文库爬虫(免下载券)](https://www.jianshu.com/p/c8e10ec26342)

## [Django template 复用](https://www.cnblogs.com/zealousness/p/8757144.html)

## 飞书接入

- [机器人和消息会话事件](https://open.feishu.cn/document/ukTMukTMukTM/uMTNxYjLzUTM24yM1EjN)
- [发送文本消息](https://open.feishu.cn/document/ukTMukTMukTM/uUjNz4SN2MjL1YzM)

## 小程序扫码登录流程说明

前端生成一张二维码（就是一个url 含有唯一标志），请求后端接口保存二维码的唯一标志、过期时间以及状态，
前端带上唯一标志轮询后端接口，判断该二维码的状态是否改变，如果改变，则表示已登录

用户使用小程序进行扫码，带上用户信息、二维码唯一标志，更新数据库二维码的状态

## Tools

- [Aliyun OSS](https://oss.console.aliyun.com/bucket/oss-cn-hangzhou/ncucoder/overview)
