FROM registry.cn-hangzhou.aliyuncs.com/resium/resium-api-base:latest
LABEL maintainer="K8sCat <k8scat@gmail.com>"
WORKDIR /data/resium-api
EXPOSE 8000
COPY . .
RUN chmod +x ./entrypoint.sh
ENTRYPOINT [ "./entrypoint.sh" ]
