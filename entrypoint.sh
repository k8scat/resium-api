#!/bin/bash

# python manage.py runserver 0.0.0.0:8000 --insecure --settings=csdnbot.settings.prod
gunicorn csdnbot.wsgi -w 4 -k gthread -b 0.0.0.0:8000