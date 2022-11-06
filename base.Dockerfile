FROM python:3.10.8-alpine
LABEL maintainer="K8sCat <k8scat@gmail.com>"
COPY requirements.txt .
ENV TZ="Asia/Shanghai"
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories \
    && apk add --no-cache \
        mariadb-dev \
        gcc \
        musl-dev \
        libffi-dev \
        jpeg-dev \
        libxml2-dev \
        libxslt-dev \
        tzdata \
    && pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip install -U pip \
    && pip install -r requirements.txt \
    && rm -f requirements.txt
