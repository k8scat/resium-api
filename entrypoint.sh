#!/bin/bash

uwsgi uwsgi.ini &
mv csdnbot-nginx.conf /etc/nginx/conf.d/
nginx -g daemon off;
