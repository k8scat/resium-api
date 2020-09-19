#!/bin/bash

# 停止服务
docker-compose down
# 删除旧的镜像
docker rmi resium

# 更新基础镜像
docker pull registry.cn-hangzhou.aliyuncs.com/hsowan/python37-django:latest
# 删除none镜像
noneImageIDs=$(docker images | grep '<none>' | awk 'NR!=1 {print $3}')
for imageID in ${noneImageIDs[@]}
do
  docker rmi $imageID
done

# 启动并重新构建镜像
docker-compose up -d