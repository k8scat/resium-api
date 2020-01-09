#!/bin/bash

docker-compose down
docker rmi csdnbot
docker-compose up -d