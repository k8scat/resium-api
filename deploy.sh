#!/bin/bash

BASE_IMAGE="registry.cn-hangzhou.aliyuncs.com/hsowan/python37-django:latest"
RESIUM_API="resium-api:latest"

start_mysql(){
	mysql_existed=`docker ps | grep "resium-mysql"`
	if [ -z "${mysql_existed}" ];then
		cd mysql
		docker-compose down
		echo "docker-compose up -d"
		docker-compose up -d
		cd -
	else
		echo "resium-mysql existed"
	fi
}

start_redis(){
  redis_existed=`docker ps | grep "resium-redis"`
	if [ -z "${redis_existed}" ];then
		docker-compose -f redis-prod.yml down
		echo "docker-compose -f redis-prod.yml up -d"
		docker-compose -f redis-prod.yml up -d
	else
		echo "resium-redis existed"
	fi
}

update_resium(){
	# 停止服务
	docker-compose down
	# 删除旧的镜像
	docker rmi ${RESIUM_API} || true

	# 更新基础镜像
	docker rmi ${BASE_IMAGE} && docker pull ${BASE_IMAGE} || true

	# 删除 none 镜像
	# noneImageIDs=$(docker images | grep '<none>' | awk 'NR!=1 {print $3}')
	# for imageID in ${noneImageIDs[@]}
	# do
	#   docker rmi $imageID
	# done

	# 启动并重新构建镜像
	docker-compose up -d
}

start_mysql
start_redis
update_resium
