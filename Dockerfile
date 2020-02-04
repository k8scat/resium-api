FROM registry.cn-hangzhou.aliyuncs.com/hsowan/python37-django:latest

LABEL maintainer="hsowan <hsowan.me@gmail.com>"

WORKDIR /csdnbot

EXPOSE 80

COPY . .
COPY ./csdnbot.conf /etc/nginx/conf.d/

ENTRYPOINT [ "./entrypoint.sh" ]