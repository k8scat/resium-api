FROM python:3.10.8-alpine
LABEL maintainer="K8sCat <k8scat@gmail.com>"
ENV TZ="Asia/Shanghai"
WORKDIR /data/resium-api
COPY . .
RUN apk add --no-cache \
        mariadb-dev \
        gcc \
        musl-dev \
        libffi-dev \
        jpeg-dev \
        libxml2-dev \
        libxslt-dev \
        tzdata
RUN pip install -U pip \
    && pip install -r requirements.txt \
    && python manage.py collectstatic
RUN chmod +x ./entrypoint.sh
EXPOSE 8000
ENTRYPOINT [ "./entrypoint.sh" ]
