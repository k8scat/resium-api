FROM registry.cn-hangzhou.aliyuncs.com/resium/resium-api-base:0.0.1
LABEL maintainer="hsowan <hsowan.me@gmail.com>"
ENV TZ Asia/Shanghai
WORKDIR /data/resium-api
EXPOSE 8000
COPY . .
RUN chmod +x ./entrypoint.sh
ENTRYPOINT [ "./entrypoint.sh" ]
