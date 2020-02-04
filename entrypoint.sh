#!/bin/bash

uwsgi uwsgi.ini &
nginx -c /csdnbot/nginx.conf
