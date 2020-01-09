#!/bin/bash

pipenv run python manage.py makemigrations downloader
pipenv run python manage.py migrate


