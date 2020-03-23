# https://git.ncucoder.com/hsowan/python37-django
FROM registry.cn-hangzhou.aliyuncs.com/hsowan/python37-django:latest

LABEL maintainer="hsowan <hsowan.me@gmail.com>"

WORKDIR /resium

EXPOSE 8000

COPY . .

ENTRYPOINT [ "./entrypoint.sh" ]
