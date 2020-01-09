#!/bin/bash

tag='latest'
image='csdnbot'

# 判断是否已有容器存在，有的话则停止并删除相应容器
existed_service=$(docker ps -a | awk '{print $2}' | grep '^'${image}':'${tag}'$' )
if [ "${existed_service}" == "" ]; then
  echo 'service not exist'
else
  docker-compose down
fi

# 判断是否已有镜像存在，有的话则删除
existed_image=$(docker images | awk '{print $1}' | grep '^'${image}'$')
if [ "${existed_image}" == "" ]; then
  echo 'image not exist'
else
  docker rmi ${image}':'${tag}
fi

docker-compose up -d
