FROM registry.cn-hangzhou.aliyuncs.com/hsowan/python37-django:latest

LABEL maintainer="hsowan <hsowan.me@gmail.com>"

WORKDIR /csdnbot

EXPOSE 80

COPY . .

ENTRYPOINT [ "./entrypoint.sh" ]