dev:
	python manage.py runserver 0:8000

build-image:
	docker build -t resium-api:latest .

install-venv:
	pip3 install --user virtualenv
	virtualenv -p python3 .venv

enable-venv:
	source .venv/bin/activate

install-mysqlclient:
	yum install -y mysql-devel

install-requirements:
	pip install -r requirements.txt

collectstatic:
	mkdir -p logs
	python manage.py collectstatic