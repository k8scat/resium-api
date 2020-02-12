#!/bin/bash

python manage.py makemigrations downloader --settings=csdnbot.settings.prod
python manage.py migrate --settings=csdnbot.settings.prod