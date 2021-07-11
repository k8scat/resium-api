#!/bin/bash

# python manage.py runserver 0.0.0.0:8000 --insecure --settings=resium.settings.prod

gunicorn resium.wsgi -w 4 -k gthread -b 0.0.0.0:8000