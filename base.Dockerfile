FROM python:3.8.2-alpine
LABEL maintainer="hsowan <hsowan.me@gmail.com>"
COPY requirements.txt .
RUN apk add --no-cache \
        mariadb-dev \
        gcc \
        musl-dev \
        libffi-dev \
        jpeg-dev \
        libxml2-dev \
        libxslt-dev \
        tzdata \
    && pip install -U pip \
    && pip install -r requirements.txt \
    && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
