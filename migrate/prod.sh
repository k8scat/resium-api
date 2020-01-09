#!/bin/bash

pipenv run python manage.py makemigrations downloader --settings=csdnbot.settings.prod
pipenv run python manage.py migrate --settings=csdnbot.settings.prod