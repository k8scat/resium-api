FROM python:3.10.8-alpine
LABEL maintainer="K8sCat <k8scat@gmail.com>"
COPY requirements.txt .
ENV TZ="Asia/Shanghai"
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
    && rm -f requirements.txt
