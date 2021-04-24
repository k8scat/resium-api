FROM python:3.7-alpine
LABEL maintainer="hsowan <hsowan.me@gmail.com>"
ENV TZ Asia/Shanghai
WORKDIR /data/resium-api
EXPOSE 8000
COPY . .
RUN mkdir -p logs upload download && \
    apk add --no-cache mariadb-dev gcc musl-dev libffi-dev jpeg-dev libxml2-dev libxslt-dev && \
    pip install -r requirements.txt
ENTRYPOINT [ "gunicorn", "resium.wsgi", "-w", "4", "-k", "gthread", "-b", "0.0.0.0:8000" ]
