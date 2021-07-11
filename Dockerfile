FROM python:3.8.2-alpine
LABEL maintainer="hsowan <hsowan.me@gmail.com>"
ENV TZ Asia/Shanghai
WORKDIR /data/resium-api
EXPOSE 8000
COPY . .
RUN apk add --no-cache mariadb-dev gcc musl-dev libffi-dev jpeg-dev libxml2-dev libxslt-dev && \
    pip install -U pip && \
    pip install -r requirements.txt && \
    chmod +x ./entrypoint.sh

ENTRYPOINT [ "./entrypoint.sh" ]
