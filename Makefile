dev:
	python manage.py runserver 0:8000

build-image:
	docker build -t resium-api:latest .