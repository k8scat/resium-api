#!/bin/bash

python manage.py makemigrations downloader --settings=resium.settings.prod
python manage.py migrate --settings=resium.settings.prod