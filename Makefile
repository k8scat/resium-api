python = python3
pip = pip3

dev:
	$(python) manage.py runserver 0:8000

build-image:
	docker build -t resium-api:latest .

install-virtualenv:
	$(pip) install --user virtualenv

new-venv:
	virtualenv -p python3 .venv

enable-venv:
	. .venv/bin/activate

install-mysqlclient:
	yum install -y mysql-devel

install-requirements:
	$(pip) install -r requirements.txt

collectstatic:
	mkdir -p logs
	$(python) manage.py collectstatic

# 
createsuperuser:
	python manage.py createsuperuser

migrate-dev:
	python manage.py makemigrations downloader
	python manage.py migrate

migrate-prod:
	python manage.py makemigrations downloader --settings=resium.settings.prod
	python manage.py migrate --settings=resium.settings.prod
